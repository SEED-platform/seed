# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.contrib.postgres.aggregates.general import ArrayAgg

from django.db.models import Subquery
from django.db.models.aggregates import Count

from seed.models import (
    Column,
    Cycle,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLotAuditLog,
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
        AuditLogClass = PropertyAuditLog
    elif StateClassName == 'TaxLotState':
        StateClass = TaxLotState
        ViewClass = TaxLotView
        AuditLogClass = TaxLotAuditLog

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
        AuditLogClass.objects.
        filter(state_id__in=Subquery(state_matches.values('id'))).
        order_by('created').
        values_list('state_id', flat=True)
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
    """
    Scope: all PropertyViews and TaxLotViews for an Org.
    Algorithm:
        - Start with PropertyViews then repeat for TaxLotViews
            - For each Cycle,
            - Looking at the corresponding -States attached to these -Views,...
            - Disregard/ignore any -States where all matching criteria is None (likely a subquery or extra exclude).
            - Group together IDs of -States that match each other.
            - For each group of size larger than 1, run manual merging logic so
            that there's only one record left but make the -AuditLog a "System Match".
    """
    summary = {
        'PropertyState': {
            'merged_count': 0,
            'new_merged_state_ids': []
        },
        'TaxLotState': {
            'merged_count': 0,
            'new_merged_state_ids': []
        },
    }

    for StateClass in (PropertyState, TaxLotState):
        ViewClass = PropertyView if StateClass == PropertyState else TaxLotView

        column_names = matching_criteria_column_names(org_id, StateClass.__name__)
        cycle_ids = Cycle.objects.filter(organization_id=org_id).values_list('id', flat=True)
        for cycle_id in cycle_ids:
            existing_cycle_views = ViewClass.objects.filter(cycle_id=cycle_id)
            matched_id_groups = StateClass.objects.\
                filter(id__in=Subquery(existing_cycle_views.values('state_id'))).\
                exclude(**empty_criteria_filter(org_id, StateClass)).\
                values(*column_names).\
                annotate(matched_ids=ArrayAgg('id'), matched_count=Count('id')).\
                values_list('matched_ids', flat=True).\
                filter(matched_count__gt=1)

            for state_ids in matched_id_groups:
                state_ids.sort()  # Ensures priority given to most recently uploaded record
                merged_state = merge_states_with_views(state_ids, org_id, 'System Match', StateClass)

                summary[StateClass.__name__]['merged_count'] += len(state_ids)
                summary[StateClass.__name__]['new_merged_state_ids'].append(merged_state.id)

    return summary
