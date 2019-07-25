# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.contrib.postgres.aggregates.general import ArrayAgg

from django.db import transaction
from django.db.models import Subquery
from django.db.models.aggregates import Count

from seed.models import (
    Column,
    Cycle,
    PropertyState,
    PropertyView,
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotState,
    TaxLotView,
)
from seed.utils.merge import merge_states_with_views


def empty_criteria_filter(organization_id, StateClass):
    """
    Using an empty -State, return a dict that can be used as a QS filter
    to search for -States where all matching criteria values are None.
    """
    empty_state = StateClass()
    return matching_filter_criteria(
        organization_id,
        StateClass.__name__,
        empty_state
    )


def matching_filter_criteria(organization_id, table_name, state):
    """
    For a given -State, returns a dictionary of it's matching criteria values.

    This dictionary is frequently unpacked for a QuerySet filter or exclude.
    """
    return {
        column_name: getattr(state, column_name, None)
        for column_name
        in matching_criteria_column_names(organization_id, table_name)
    }


def matching_criteria_column_names(organization_id, table_name):
    """
    Collect matching criteria columns while replacing address_line_1 with
    normalized_address if applicable. A Python set is returned to handle the
    case where normalized_address might show up twice, which shouldn't really
    happen anyway.
    """
    return {
        'normalized_address' if c.column_name == "address_line_1" else c.column_name
        for c
        in Column.objects.filter(
            organization_id=organization_id,
            is_matching_criteria=True,
            table_name=table_name
        )
    }


def match_merge_in_cycle(view_id, StateClassName):
    """
    Given a -View ID, this method matches and merges for the related -State.
    Match-eligible -States are scoped to those associated with -Views within
    the same Cycle.

    If the -State associated with the -View doesn't have any matching criteria
    values populated, the -State is not eligible for a match merge.
    """
    if StateClassName == 'PropertyState':
        StateClass = PropertyState
        ViewClass = PropertyView
    elif StateClassName == 'TaxLotState':
        StateClass = TaxLotState
        ViewClass = TaxLotView

    view = ViewClass.objects.get(pk=view_id)
    org_id = view.state.organization_id

    # Check if associated -State has empty matching criteria.
    if StateClass.objects.filter(pk=view.state_id, **empty_criteria_filter(org_id, StateClass)).exists():
        return 0, None

    matching_criteria = matching_filter_criteria(org_id, StateClassName, view.state)
    views_in_cycle = ViewClass.objects.filter(cycle_id=view.cycle_id)
    state_matches = StateClass.objects.filter(
        pk__in=Subquery(views_in_cycle.values('state_id')),
        **matching_criteria
    ).exclude(pk=view.state_id)

    state_ids = list(
        state_matches.order_by('updated').values_list('id', flat=True)
    )
    state_ids.append(view.state_id)  # Excluded above and appended to give merge precedence
    count = len(state_ids)

    if count > 1:
        # The following merge action ignores merge protection and prioritizes -States by most recent AuditLog
        merged_state = merge_states_with_views(state_ids, org_id, 'System Match', StateClass)
        view_id = ViewClass.objects.get(state_id=merged_state.id).id
        return count, view_id
    elif count == 1:
        return 0, None


def match_merge_link(view_id, StateClassName):
    if StateClassName == 'PropertyState':
        CanonicalClass = Property
        StateClass = PropertyState
        ViewClass = PropertyView
        AuditLogClass = PropertyAuditLog
        canonical_id_col = 'property_id'
    elif StateClassName == 'TaxLotState':
        CanonicalClass = TaxLot
        StateClass = TaxLotState
        ViewClass = TaxLotView
        AuditLogClass = TaxLotAuditLog
        canonical_id_col = 'taxlot_id'

    view = ViewClass.objects.get(pk=view_id)
    org_id = view.state.organization_id
    view_cycle_id = view.cycle_id

    # Check if associated -State has empty matching criteria.
    if StateClass.objects.filter(pk=view.state_id, **empty_criteria_filter(org_id, StateClass)).exists():
        return

    matching_criteria = matching_filter_criteria(org_id, StateClassName, view.state)
    state_appended_matching_criteria = {
        'state__' + col_name: v
        for col_name, v
        in matching_criteria.items()
    }

    # Get all matching views
    matching_views = ViewClass.objects.\
        prefetch_related('state').\
        filter(**state_appended_matching_criteria)

    # Group them by cycle and capture state_ids to be merged
    states_to_merge = matching_views.values('cycle_id').\
        annotate(state_ids=ArrayAgg('state_id'), match_count=Count('id')).\
        filter(match_count__gt=1).\
        values_list('state_ids', flat=True)

    for state_ids in states_to_merge:
        ordered_ids = list(
            AuditLogClass.objects.
            filter(state_id__in=state_ids).
            order_by('created').
            values_list('state_id', flat=True)
        )
        merge_states_with_views(ordered_ids, org_id, 'System Match', StateClass)

    # Account for case when incoming view was part of in-Cycle merges...
    refreshed_view = matching_views.get(cycle_id=view_cycle_id)

    """
    Amongst the matched views excluding the target view, run through the following cases:
    - No matches found - check for links and diassociate if necessary
    - All matches are linked already - use the linking ID
    - All matches are NOT linked already - use new canonical record to link
    """

    # If no matches found - check for past links and diassociate if necessary
    if matching_views.exclude(id=refreshed_view.id).exists() is False:
        canonical_id_dict = {canonical_id_col: getattr(refreshed_view, canonical_id_col)}
        previous_links = ViewClass.objects.filter(**canonical_id_dict).exclude(id=refreshed_view.id)
        if previous_links.exists():
            new_record = CanonicalClass.objects.create(organization_id=org_id)

            if CanonicalClass == Property:
                new_record.copy_meters(refreshed_view.property_id)

            setattr(refreshed_view, canonical_id_col, new_record.id)
            refreshed_view.save()

        return

    # Exclude target and capture ordered, unique canonical IDs
    # Ordered to prioritize most recently created records when copying Meters
    unique_canonical_ids = matching_views.\
        exclude(id=refreshed_view.id).\
        order_by('id').\
        values(canonical_id_col).\
        annotate().\
        values_list(canonical_id_col, flat=True)

    if unique_canonical_ids.count() == 1:
        # If all matches are linked already - use the linking ID
        setattr(refreshed_view, canonical_id_col, unique_canonical_ids.first())
        refreshed_view.save()
    else:
        # All matches are NOT linked already - use new canonical record to link
        new_record = CanonicalClass.objects.create(organization_id=org_id)

        if CanonicalClass == Property:
            for id in unique_canonical_ids:
                new_record.copy_meters(id)

        canonical_id_dict = {canonical_id_col: new_record.id}

        matching_views.update(**canonical_id_dict)


def whole_org_match_merge_link(org_id):
    """
    For a given organization, run a match merge round for each cycle in
    isolation. Afterwards, run a match link round across all cycles at once.

    In this context, a Property/TaxLot Set refers to the -State, canonical
    record, and -View records associated by the -View.

    Algorithm - Run for Property Sets then for TaxLot Sets:
        For each Cycle, run match and merges.
            - Focus on -States associated with -Views in this Cycle.
            - Ignore -States where all matching criteria is None.
            - Group -State IDs by whether they match each other.
            - Ignore each groups of size size 1 (not matched).
            - For each remaining group, run merge logic so that there's only one
            Set left. Any labels, notes, pairings, and meters are transferred to
            and persisted in this Set.

        Across all Cycles, run match and links.
            - Focus on all -States and canonical records associated to -Views
            in this organization.
            - Ignore -Views with -States where all matching criteria is None.
            - Identify canonical records that currently have no links. These are
            unaffected during this process if the record remains unlinked.
            - Group canonical IDs and -View IDs according to whether their
            associated -States match each other.
            - Ignore groups of size 1 where the single member was previously
            unlinked as well.
            - For each remaining group, apply a new canonical record to the
            each of -Views in this group. Any meters are transferred to this
            new canonical record.
    """
    summary = {
        'PropertyState': {
            'merged_count': 0,
            'linked_sets_count': 0,
        },
        'TaxLotState': {
            'merged_count': 0,
            'linked_sets_count': 0,
        },
    }

    cycle_ids = Cycle.objects.filter(organization_id=org_id).values_list('id', flat=True)

    for StateClass in (PropertyState, TaxLotState):
        ViewClass = PropertyView if StateClass == PropertyState else TaxLotView
        CanonicalClass = Property if StateClass == PropertyState else TaxLot

        column_names = matching_criteria_column_names(org_id, StateClass.__name__)
        empty_matching_criteria = empty_criteria_filter(org_id, StateClass)

        # Match merge within each Cycle
        with transaction.atomic():
            for cycle_id in cycle_ids:
                view_in_cycle = ViewClass.objects.filter(cycle_id=cycle_id)

                matched_id_groups = StateClass.objects.\
                    filter(id__in=Subquery(view_in_cycle.values('state_id'))).\
                    exclude(**empty_matching_criteria).\
                    values(*column_names).\
                    annotate(matched_ids=ArrayAgg('id'), matched_count=Count('id')).\
                    values_list('matched_ids', flat=True).\
                    filter(matched_count__gt=1)

                for state_ids in matched_id_groups:
                    merge_states_with_views(state_ids, org_id, 'System Match', StateClass)

                    summary[StateClass.__name__]['merged_count'] += len(state_ids)

        # Match link across the whole Organization
        with transaction.atomic():
            # Append 'state__' to dict keys used for filtering so that filtering can be done across associations
            state_appended_col_names = {'state__' + col_name for col_name in column_names}
            state_appended_empty_matching_criteria = {
                'state__' + col_name: v
                for col_name, v
                in empty_matching_criteria.items()
            }

            # Scope -View - ignoring those associated to -States with empty matching critieria.
            org_views = ViewClass.objects.\
                filter(cycle_id__in=cycle_ids).\
                select_related('state').\
                exclude(**state_appended_empty_matching_criteria)

            canonical_id_col = 'property_id' if StateClass == PropertyState else 'taxlot_id'

            # Identify all canonical_ids that are used once and are potentially reusable
            reusable_canonical_ids = org_views.\
                values(canonical_id_col).\
                annotate(use_count=Count(canonical_id_col)).\
                values_list(canonical_id_col, flat=True).\
                filter(use_count=1)

            link_groups = org_views.\
                values(*state_appended_col_names).\
                annotate(
                    canonical_ids=ArrayAgg(canonical_id_col),
                    view_ids=ArrayAgg('id'),
                    link_count=Count('id')
                ).\
                values_list('canonical_ids', 'view_ids', 'link_count')

            unused_canonical_ids = []
            for canonical_ids, view_ids, link_count in link_groups:
                # If the canonical record was unlinked and is still unlinked, do nothing
                if link_count == 1 and canonical_ids[0] in reusable_canonical_ids:
                    continue

                # Otherwise, create a new canonical record, copy meters if applicable, and apply the new record to old -Views
                new_record = CanonicalClass.objects.create(organization_id=org_id)

                if CanonicalClass == Property:
                    canonical_ids.sort(reverse=True)  # Ensures priority given by most recently created canonical record
                    for canonical_id in canonical_ids:
                        new_record.copy_meters(canonical_id, source_persists=True)

                ViewClass.objects.filter(id__in=view_ids).update(**{canonical_id_col: new_record.id})

                summary[StateClass.__name__]['linked_sets_count'] += 1

                unused_canonical_ids += canonical_ids

            # Delete canonical records that are no longer used.
            CanonicalClass.objects.filter(id__in=unused_canonical_ids).delete()

    return summary
