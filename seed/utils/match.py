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
    PropertyState,
    PropertyView,
    TaxLotState,
    TaxLotView,
)
from seed.utils.merge import merge_states_with_views


def empty_criteria_states_qs(state_ids, organization_id, ObjectStateClass):
    """
    Using an empty -State, return a QS that searches for -States within a given
    group that where all matching criteria values are None.
    """
    empty_state = ObjectStateClass()
    empty_criteria_filter = matching_filter_criteria(
        organization_id,
        ObjectStateClass.__name__,
        empty_state
    )

    return ObjectStateClass.objects.filter(
        pk__in=state_ids,
        **empty_criteria_filter
    )


def matching_filter_criteria(organization_id, table_name, state):
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


def match_merge_in_cycle(view_id, StateClassName):# TODO: add check for all empty.
    if StateClassName == 'PropertyState':
        StateClass = PropertyState
        ViewClass = PropertyView
    elif StateClassName == 'TaxLotState':
        StateClass = TaxLotState
        ViewClass = TaxLotView

    view = ViewClass.objects.get(pk=view_id)
    org_id = view.state.organization_id
    matching_criteria = matching_filter_criteria(org_id, StateClassName, view.state)
    views_in_cycle = ViewClass.objects.filter(cycle_id=view.cycle_id)
    state_matches = StateClass.objects.filter(
        pk__in=Subquery(views_in_cycle.values('state_id')),
        **matching_criteria
    ).exclude(pk=view.state_id)

    state_ids = list(state_matches.order_by('id').values_list('id', flat=True))
    state_ids.append(view.state_id)  # Excluded above and appended to give merge precedence
    count = len(state_ids)

    if count > 1:
        merged_state = merge_states_with_views(state_ids, org_id, 'System Match', StateClass)
        view_id = ViewClass.objects.get(state_id=merged_state.id).id
        return count, view_id
    elif count == 1:
        return 0, None


def org_level_match_merge(organization_id):
    """
    Scope: all PropertyViews and TaxLotViews for an Org
    Algorithm:
        - Start with PropertyViews then repeat for TaxLotViews
            - For each Cycle,
            - Looking at the corresponding -States attached to these -Views,...
            - Disregard/ignore any -States where all matching criteria is None (likely a subquery or extra exclude)
            - Group together -States that match each other.
            - For each group, run manual merging logic so that there's only one
            record left but make the -AuditLog a "System Match"
    """
    for ObjectStateClass in (PropertyState, TaxLotState):
        table_name = ObjectStateClass.__name__
        column_names = matching_criteria_column_names(organization_id, table_name)
        cycle_ids = Cycle.objects.filter(organization_id=organization_id).values_list('id', flat=True)
        for cycle_id in cycle_ids:
            existing_cycle_views = PropertyView.objects.filter(cycle_id=cycle_id)
            matched_id_groups = ObjectStateClass.objects.\
                filter(id__in=Subquery(existing_cycle_views.values('state_id'))).\
                values(*column_names).\
                annotate(matched_ids=ArrayAgg('id'), matched_count=Count('id')).\
                values_list('matched_ids', flat=True).\
                filter(matched_count__gt=1)
            # for id_group in matched_id_groups:
            #     match_merge_in_cycle(id_group)
