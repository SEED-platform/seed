# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from celery import shared_task

from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import transaction
from django.db.models import Subquery
from django.db.models.aggregates import Count

from seed.models import (
    Column,
    Cycle,
    Property,
    PropertyState,
    PropertyView,
    TaxLot,
    TaxLotState,
    TaxLotView,
)
from seed.utils.merge import merge_states_with_views
from seed.utils.properties import properties_across_cycles
from seed.utils.taxlots import taxlots_across_cycles


def empty_criteria_filter(StateClass, column_names):
    """
    Using an empty -State, return a dict that can be used as a QS filter
    to search for -States where all matching criteria values are None.
    """
    empty_state = StateClass()
    return matching_filter_criteria(empty_state, column_names)


def matching_filter_criteria(state, column_names):
    """
    For a given -State, returns a dictionary of it's matching criteria values.

    This dictionary is frequently unpacked for a QuerySet filter or exclude.
    """
    return {
        column_name: getattr(state, column_name, None)
        for column_name
        in column_names
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


def _merge_matches_across_cycles(matching_views, org_id, given_state_id, StateClass):
    """
    This is a helper method for match_merge_link().

    Given a QS of matching -Views, group them by Cycle. Merge the corresponding
    -States of each group with priority given based on most recent AuditLog.

    If the given -View/-State has matches in its own Cycle, AuditLogs are still
    used to determine merge order, but overarching precedence is given to the
    provided -View's -State.

    The count of merges as well as the target -State ID is returned. The target
    -State ID is either the given -State ID or the merged -State ID of merges
    involving the given -State ID.
    """
    # Group matching -Views by Cycle and capture state_ids to be merged
    # For the purpose of merging, we only care if match_count is greater than 1.
    states_to_merge = matching_views.values('cycle_id').\
        annotate(state_ids=ArrayAgg('state_id'), match_count=Count('id')).\
        filter(match_count__gt=1).\
        values_list('state_ids', flat=True)

    target_state_id = given_state_id
    count = 0

    for state_ids in states_to_merge:
        ordered_ids = list(
            StateClass.objects.
            filter(id__in=state_ids).
            order_by('updated').
            values_list('id', flat=True)
        )

        if given_state_id in ordered_ids:
            # If the given -State ID is included, give it precedence and
            # capture resulting merged_state ID to be returned
            ordered_ids.remove(given_state_id)
            ordered_ids.append(given_state_id)
            merged_state = merge_states_with_views(ordered_ids, org_id, 'System Match', StateClass)
            target_state_id = merged_state.id
        else:
            merge_states_with_views(ordered_ids, org_id, 'System Match', StateClass)

        count += len(ordered_ids)

    return count, target_state_id


def _link_matches(matching_views, org_id, view, ViewClass):
    """
    This is a helper method for match_merge_link() and is intended to be called
    after match merges have occurred.

    Given a QS of matching -Views, the following cases are handled:
    1. No matches found - check for pre-existing links and, if necessary,
    diassociate the given -View
    2. All matches are linked already - use the currently existing linking ID to
    link the given -View
    3. All matches are NOT linked already - use new canonical record to link the
    matching and given -Views

    In the end, return the count of matches as this represents the number of links.
    """
    if ViewClass == PropertyView:
        CanonicalClass = Property
        canonical_id_col = 'property_id'
    elif ViewClass == TaxLotView:
        CanonicalClass = TaxLot
        canonical_id_col = 'taxlot_id'

    # Exclude target and capture unique canonical IDs
    unique_canonical_ids = matching_views.\
        exclude(id=view.id).\
        values(canonical_id_col).\
        annotate(state_ids=ArrayAgg(canonical_id_col)).\
        values_list(canonical_id_col, flat=True)

    if unique_canonical_ids.exists() is False:
        # If no matches found - check for past links and diassociate if necessary
        canonical_id_dict = {canonical_id_col: getattr(view, canonical_id_col)}
        previous_links = ViewClass.objects.filter(**canonical_id_dict).exclude(id=view.id)
        if previous_links.exists():
            new_record = CanonicalClass.objects.create(organization_id=org_id)

            if CanonicalClass == Property:
                new_record.copy_meters(view.property_id)

            setattr(view, canonical_id_col, new_record.id)
            view.save()
    elif unique_canonical_ids.count() == 1:
        # If all matches are linked already - use the linking ID
        linking_id = unique_canonical_ids.first()

        if CanonicalClass == Property:
            linking_property = Property.objects.get(id=linking_id)
            linking_property.copy_meters(view.property_id)

        setattr(view, canonical_id_col, linking_id)

        view.save()
    else:
        # In this case, all matches are NOT linked already - use new canonical record to link
        new_record = CanonicalClass.objects.create(organization_id=org_id)

        if CanonicalClass == Property:
            # Copy meters by highest ID order and lastly for the given Property
            sorted_canonical_ids = sorted(list(unique_canonical_ids))
            sorted_canonical_ids.append(view.property_id)
            for id in sorted_canonical_ids:
                new_record.copy_meters(id)

        canonical_id_dict = {canonical_id_col: new_record.id}

        matching_views.update(**canonical_id_dict)

    return matching_views.count() - 1


def match_merge_link(view_id, StateClassName):
    """
    This method receives a -View's ID, checks for matches for that -View's
    -State across Cycles, merges matches where there are multiple in a Cycle,
    and finally after there are at most one match in any Cycle, creates links
    between the matching -Views.

    This method returns the total count of merged -States, the number of links
    as well as the target -View if merges did occur (whether it was
    updated or not).
    """
    if StateClassName == 'PropertyState':
        StateClass = PropertyState
        ViewClass = PropertyView
    elif StateClassName == 'TaxLotState':
        StateClass = TaxLotState
        ViewClass = TaxLotView

    view = ViewClass.objects.get(pk=view_id)
    given_state_id = view.state_id
    org_id = view.state.organization_id

    column_names = matching_criteria_column_names(org_id, StateClassName)

    # If associated -State has empty matching criteria, do nothing
    empty_matching_criteria = empty_criteria_filter(StateClass, column_names)
    if StateClass.objects.filter(pk=given_state_id, **empty_matching_criteria).exists():
        return 0, 0, None

    # 'state__' is appended to be able to query from the related -View Class
    matching_criteria = matching_filter_criteria(view.state, column_names)
    state_appended_matching_criteria = {
        'state__' + col_name: v
        for col_name, v
        in matching_criteria.items()
    }

    # Get all matching views (across Cycles in this Organization)
    matching_views = ViewClass.objects.\
        prefetch_related('state').\
        filter(
            state__organization_id=org_id,
            **state_appended_matching_criteria
        )

    merge_count, target_state_id = _merge_matches_across_cycles(matching_views, org_id, given_state_id, StateClass)

    # Refresh target_view in case merges changed the target -View in last step.
    target_view = ViewClass.objects.get(state_id=target_state_id)

    link_count = _link_matches(matching_views, org_id, target_view, ViewClass)

    if merge_count > 0:
        return merge_count, link_count, target_view.id
    else:
        return 0, link_count, None


@shared_task(serializer='pickle', ignore_result=True)
def whole_org_match_merge_link(org_id, state_class_name, proposed_columns=[]):
    """
    For a given organization, run a match merge round for each cycle in
    isolation. Afterwards, run a match link round across all cycles at once.

    In this context, a Property/TaxLot Set refers to the -State, canonical
    record, and -View records associated by the -View.

    Algorithm - Run for either Property Sets or for TaxLot Sets:
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
            - Identify canonical records that currently have no links. These are
            unaffected during this process if the record remains unlinked. Also,
            these are canonical records that can potentially be reused.
            - Scope the next steps to ignore -Views with -States where all
            matching criteria is None.
            - Create link groups of canonical IDs and -View IDs according to
            whether their associated -States match each other.
            - Ignore groups of size 1 where the single member was previously
            unlinked as well.
            - For each remaining group, apply a new canonical record to
            each of -Views in this group. Any meters are transferred to this
            new canonical record.
            - For any records that had empty (all None) matching criteria
            values, disassociate any previous links by applying a new canonical
            record to each.
            - Delete any unused canonical records.
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

    if state_class_name == 'PropertyState':
        StateClass = PropertyState
        ViewClass = PropertyView
        CanonicalClass = Property
    elif state_class_name == 'TaxLotState':
        StateClass = TaxLotState
        ViewClass = TaxLotView
        CanonicalClass = TaxLot

    if proposed_columns:
        # Use column names as given (replacing address_line_1 with normalized_address)
        column_names = [
            column_name if column_name != 'address_line_1' else 'normalized_address'
            for column_name
            in proposed_columns
        ]
        preview_run = True
    else:
        column_names = matching_criteria_column_names(org_id, state_class_name)
        preview_run = False

    empty_matching_criteria = empty_criteria_filter(StateClass, column_names)

    with transaction.atomic():
        # Match merge within each Cycle
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
                ordered_ids = list(
                    StateClass.objects.
                    filter(id__in=state_ids).
                    order_by('updated').
                    values_list('id', flat=True)
                )

                merge_states_with_views(ordered_ids, org_id, 'System Match', StateClass)

                summary[StateClass.__name__]['merged_count'] += len(state_ids)

        # Match link across the whole Organization
        # Append 'state__' to dict keys used for filtering so that filtering can be done across associations
        state_appended_col_names = {'state__' + col_name for col_name in column_names}
        state_appended_empty_matching_criteria = {
            'state__' + col_name: v
            for col_name, v
            in empty_matching_criteria.items()
        }

        canonical_id_col = 'property_id' if StateClass == PropertyState else 'taxlot_id'

        # Looking at all -Views in Org across Cycles
        org_views = ViewClass.objects.\
            filter(cycle_id__in=cycle_ids).\
            select_related('state')

        # Identify all canonical_ids that are currently used once and are potentially reusable
        reusable_canonical_ids = org_views.\
            values(canonical_id_col).\
            annotate(use_count=Count(canonical_id_col)).\
            values_list(canonical_id_col, flat=True).\
            filter(use_count=1)

        # Ignoring -Views associated to -States with empty matching critieria, group by columns
        link_groups = org_views.\
            exclude(**state_appended_empty_matching_criteria).\
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

        # For records with empty criteria and without reusable canonical IDs, apply a new ID.
        empty_criteria_views = ViewClass.objects.\
            select_related('state').\
            filter(cycle_id__in=cycle_ids, **state_appended_empty_matching_criteria).\
            exclude(**{canonical_id_col + "__in": reusable_canonical_ids})

        for view in empty_criteria_views:
            # Create a new canonical record, copy meters if applicable, and apply the new record to old -Views
            new_record = CanonicalClass.objects.create(organization_id=org_id)

            if CanonicalClass == Property:
                new_record.copy_meters(getattr(view, canonical_id_col), source_persists=False)

            setattr(view, canonical_id_col, new_record.id)
            view.save()

        # Also delete these unusable canonical records
        unused_canonical_ids += empty_criteria_views.values_list(canonical_id_col, flat=True)

        # Delete canonical records that are no longer used.
        CanonicalClass.objects.filter(id__in=unused_canonical_ids).delete()

        # If this was a preview run, capture results here and rollback.
        if preview_run:
            if state_class_name == 'PropertyState':
                summary = properties_across_cycles(org_id, -1, cycle_ids)
            else:
                summary = taxlots_across_cycles(org_id, -1, cycle_ids)

            transaction.set_rollback(True)

    return summary
