# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.http import JsonResponse
from rest_framework import status
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from seed.lib.superperms.orgs.models import Organization
from seed.models import (VIEW_LIST, VIEW_LIST_PROPERTY, VIEW_LIST_TAXLOT,
                         Column, ColumnListProfile, ColumnListProfileColumn,
                         Cycle, PropertyView,
                         )
from seed.search import build_view_filters_and_sorts, FilterException
from seed.models import TaxLotProperty, TaxLotView
from seed.serializers.pint import (apply_display_unit_preferences)


def _get_filtered_results(request, state_type, profile_id):
    page = request.query_params.get('page', 1)
    per_page = request.query_params.get('per_page', 1)
    org_id = request.query_params.get('organization_id')
    # org_id = get_organization(request)
    cycle_id = request.query_params.get('cycle')
    # check if there is a query paramater for the profile_id. If so, then use that one
    profile_id = request.query_params.get('profile_id', profile_id)

    if not org_id:
        return JsonResponse(
            {'status': 'error', 'message': 'Need to pass organization_id as query parameter'},
            status=status.HTTP_400_BAD_REQUEST)
    org = Organization.objects.get(id=org_id)

    if cycle_id:
        cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
    else:
        cycle = Cycle.objects.filter(organization_id=org_id).order_by('name')
        if cycle:
            cycle = cycle.first()
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Could not locate cycle',
                'pagination': {
                    'total': 0
                },
                'cycle_id': None,
                'results': []
            })

    if state_type == 'property':
        views_list = (
            PropertyView.objects.select_related('property', 'state', 'cycle')
            .filter(property__organization_id=org_id, cycle=cycle)
        )
    elif state_type == 'taxlot':
        views_list = (
            TaxLotView.objects.select_related('taxlot', 'state', 'cycle')
            .filter(taxlot__organization_id=org_id, cycle=cycle)
        )

    # Retrieve all the columns that are in the db for this organization
    columns_from_database = Column.retrieve_all(org_id, state_type, False)
    # columns_from_database = Column.retrieve_all(org_id, 'property', False)
    try:
        filters, order_by = build_view_filters_and_sorts(request.query_params, columns_from_database)
    except FilterException as e:
        return JsonResponse(
            {
                'status': 'error',
                'message': f'Error filtering: {str(e)}'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    views_list = views_list.filter(filters).order_by(*order_by)
    # Return property views limited to the 'property_view_ids' list. Otherwise, if selected is empty, return all
    if f'{state_type}_view_ids' in request.data and request.data[f'{state_type}_view_ids']:
        views_list = views_list.filter(id__in=request.data[f'{state_type}_view_ids'])

    paginator = Paginator(views_list, per_page)

    try:
        views = paginator.page(page)
        page = int(page)
    except PageNotAnInteger:
        views = paginator.page(1)
        page = 1
    except EmptyPage:
        views = paginator.page(paginator.num_pages)
        page = paginator.num_pages

    # This uses an old method of returning the show_columns. There is a new method that
    # is prefered in v2.1 API with the ProfileIdMixin.
    if state_type == 'property':
        view_list_state = VIEW_LIST_PROPERTY
    elif state_type == 'taxlot':
        view_list_state = VIEW_LIST_TAXLOT

    if profile_id is None:
        show_columns = None
    elif profile_id == -1:
        show_columns = list(Column.objects.filter(
            organization_id=org_id
        ).values_list('id', flat=True))
    else:
        try:
            profile = ColumnListProfile.objects.get(
                organization_id=org_id,
                id=profile_id,
                profile_location=VIEW_LIST,
                inventory_type=view_list_state
            )
            show_columns = list(ColumnListProfileColumn.objects.filter(
                column_list_profile_id=profile.id
            ).values_list('column_id', flat=True))
        except ColumnListProfile.DoesNotExist:
            show_columns = None

    include_related = (
        str(request.query_params.get('include_related', 'true')).lower() == 'true'
    )
    related_results = TaxLotProperty.serialize(
        views,
        show_columns,
        columns_from_database,
        include_related
    )

    # collapse units here so we're only doing the last page; we're already a
    # realized list by now and not a lazy queryset
    unit_collapsed_results = [apply_display_unit_preferences(org, x) for x in related_results]

    response = {
        'pagination': {
            'page': page,
            'start': paginator.page(page).start_index(),
            'end': paginator.page(page).end_index(),
            'num_pages': paginator.num_pages,
            'has_next': paginator.page(page).has_next(),
            'has_previous': paginator.page(page).has_previous(),
            'total': paginator.count
        },
        'cycle_id': cycle.id,
        'results': unit_collapsed_results
    }

    return JsonResponse(response)
