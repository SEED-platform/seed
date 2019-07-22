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


def whole_org_match_merge(org_id):
    # Need to revisit these comments
    """
    Scope: all PropertyViews and TaxLotViews for an Org.
    Algorithm:
        - Start with PropertyViews then repeat for TaxLotViews
        For each Cycle, run match and merges.
            - Looking at the corresponding -States attached to these -Views,...
            - Disregard/ignore any -States where all matching criteria is None (likely a subquery or extra exclude).
            - Group together IDs of -States that match each other.
            - For each group of size larger than 1, run manual merging logic so
            that there's only one record left but make the -AuditLog a "System Match".
        Across all Cycles, run match and links.
            -
    """
    # summary = {
    #     'PropertyState': {
    #         'merged_count': 0,
    #         'new_merged_state_ids': []
    #     },
    #     'TaxLotState': {
    #         'merged_count': 0,
    #         'new_merged_state_ids': []
    #     },
    # }

    cycle_ids = Cycle.objects.filter(organization_id=org_id).values_list('id', flat=True)

    for StateClass in (PropertyState, TaxLotState):
        ViewClass = PropertyView if StateClass == PropertyState else TaxLotView
        CanonicalClass = Property if StateClass == PropertyState else TaxLot

        column_names = matching_criteria_column_names(org_id, StateClass.__name__)
        empty_matching_criteria = empty_criteria_filter(org_id, StateClass)

        # Match merge within each Cycle
        with transaction.atomic():
            for cycle_id in cycle_ids:
                # Identify relevant -Views to correctly scope -States
                existing_cycle_views = ViewClass.objects.filter(cycle_id=cycle_id)

                matched_id_groups = StateClass.objects.\
                    filter(id__in=Subquery(existing_cycle_views.values('state_id'))).\
                    exclude(**empty_matching_criteria).\
                    values(*column_names).\
                    annotate(matched_ids=ArrayAgg('id'), matched_count=Count('id')).\
                    values_list('matched_ids', flat=True).\
                    filter(matched_count__gt=1)

                for state_ids in matched_id_groups:
                    state_ids.sort()# This should be sorted by auditlog  # Ensures priority given to most recently uploaded record
                    merge_states_with_views(state_ids, org_id, 'System Match', StateClass)
                    # merged_state = merge_states_with_views(state_ids, org_id, 'System Match', StateClass)

                    # summary[StateClass.__name__]['merged_count'] += len(state_ids)
                    # summary[StateClass.__name__]['new_merged_state_ids'].append(merged_state.id)

        # Match link across the whole Organization
        with transaction.atomic():
            # Append 'state__' to dict keys used for filtering so that filtering can be done across associations
            state_appended_col_names = {'state__' + col_name for col_name in column_names}
            state_appended_empty_matching_criteria = {
                'state__' + col_name: v
                for col_name, v
                in empty_matching_criteria.items()
            }

            # Scope -Views. Those associated to -States with empty critieria are ignored.
            org_views = ViewClass.objects.\
                filter(cycle_id__in=cycle_ids).\
                select_related('state').\
                exclude(**state_appended_empty_matching_criteria)

            canonical_id_col = 'property_id' if StateClass == PropertyState else 'taxlot_id'

            # Identify all canonical_ids that are only used once.
            # These are reusable if they remain unlinked.
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
                    canonical_ids.sort(reverse=True)  # Ensures priority given to most recently created record
                    for canonical_id in canonical_ids:
                        new_record.copy_meters(canonical_id, source_persists=True)

                ViewClass.objects.filter(id__in=view_ids).update(**{canonical_id_col: new_record.id})

                unused_canonical_ids += canonical_ids

            # Delete canonical records that are no longer used.
            CanonicalClass.objects.filter(id__in=unused_canonical_ids).delete()

    # return summary
