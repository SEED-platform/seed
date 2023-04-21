"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from typing import Literal, Optional, Type, Union

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.utils import DataError
from django.http import JsonResponse
from rest_framework import status
from rest_framework.request import Request

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    VIEW_LIST,
    VIEW_LIST_PROPERTY,
    VIEW_LIST_TAXLOT,
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    Cycle,
    PropertyView,
    TaxLotProperty,
    TaxLotView
)
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.search import FilterException, build_view_filters_and_sorts


def get_filtered_results(request: Request, inventory_type: Literal['property', 'taxlot'], profile_id: int) -> JsonResponse:
    page = request.query_params.get('page')
    per_page = request.query_params.get('per_page')
    org_id = request.query_params.get('organization_id')
    cycle_id = request.query_params.get('cycle')
    ids_only = request.query_params.get('ids_only', 'false').lower() == 'true'
    # check if there is a query parameter for the profile_id. If so, then use that one
    profile_id = request.query_params.get('profile_id', profile_id)
    shown_column_ids = request.query_params.get('shown_column_ids')

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
    if not cycle:
        return JsonResponse({
            'status': 'error',
            'message': 'Could not locate cycle',
            'pagination': {
                'total': 0
            },
            'cycle_id': None,
            'results': []
        })

    if ids_only and (per_page or page):
        return JsonResponse({
            'success': False,
            'message': 'Cannot pass query parameter "ids_only" with "per_page" or "page"'
        }, status=status.HTTP_400_BAD_REQUEST)

    page = page or 1
    per_page = per_page or 1

    if inventory_type == 'property':
        views_list = (
            PropertyView.objects.select_related('property', 'state', 'cycle')
            .filter(property__organization_id=org_id, cycle=cycle)
        )
    elif inventory_type == 'taxlot':
        views_list = (
            TaxLotView.objects.select_related('taxlot', 'state', 'cycle')
            .filter(taxlot__organization_id=org_id, cycle=cycle)
        )

    include_related = (
        str(request.query_params.get('include_related', 'true')).lower() == 'true'
    )

    # This uses an old method of returning the show_columns. There is a new method that
    # is preferred in v2.1 API with the ProfileIdMixin.
    if inventory_type == 'property':
        profile_inventory_type = VIEW_LIST_PROPERTY
    elif inventory_type == 'taxlot':
        profile_inventory_type = VIEW_LIST_TAXLOT

    show_columns: Optional[list[int]] = None
    if shown_column_ids and profile_id:
        return JsonResponse(
            {
                'status': 'error',
                'recommended_action': 'update_column_settings',
                'message': 'Error filtering - "shown_column_ids" and "profile_id" are mutually exclusive.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    elif shown_column_ids is not None:
        shown_column_ids = shown_column_ids.split(",")
        show_columns = list(Column.objects.filter(
            organization_id=org_id, id__in=shown_column_ids
        ).values_list('id', flat=True))
    elif profile_id is None:
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
                inventory_type=profile_inventory_type
            )
            show_columns = list(ColumnListProfileColumn.objects.filter(
                column_list_profile_id=profile.id
            ).values_list('column_id', flat=True))
        except ColumnListProfile.DoesNotExist:
            show_columns = None

    # Retrieve all the columns that are in the db for this organization
    columns_from_database = Column.retrieve_all(
        org_id=org_id,
        inventory_type=inventory_type,
        only_used=False,
        include_related=include_related,
        exclude_derived=True,
        column_ids=show_columns
    )
    try:
        filters, annotations, order_by = build_view_filters_and_sorts(request.query_params, columns_from_database)
    except FilterException as e:
        return JsonResponse(
            {
                'status': 'error',
                'message': f'Error filtering: {str(e)}'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    views_list = views_list.annotate(**annotations).filter(filters).order_by(*order_by)

    # If we are returning the children, build the childrens filters.
    if include_related:
        other_inventory_type: Literal['property', 'taxlot'] = "taxlot" if inventory_type == "property" else "property"

        other_columns_from_database = Column.retrieve_all(
            org_id=org_id,
            inventory_type=other_inventory_type,
            only_used=False,
            include_related=include_related,
            exclude_derived=True,
            column_ids=show_columns
        )
        try:
            filters, annotations, _ = build_view_filters_and_sorts(request.query_params, other_columns_from_database)
        except FilterException as e:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': f'Error filtering: {str(e)}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # If the children have filters, filter views_list by their children.
        if len(filters) > 0 or len(annotations) > 0:
            other_inventory_type_class: Union[Type[TaxLotView], Type[PropertyView]] = TaxLotView if inventory_type == "property" else PropertyView
            other_views_list = (
                other_inventory_type_class.objects.select_related(other_inventory_type, 'state', 'cycle')
                .filter(**{f'{other_inventory_type}__organization_id': org_id, 'cycle': cycle})
            )

            other_views_list = other_views_list.annotate(**annotations).filter(filters)
            taxlot_properties = TaxLotProperty.objects.filter(**{f'{other_inventory_type}_view__in': other_views_list})
            views_list = views_list.filter(taxlotproperty__in=taxlot_properties)

    # return property views limited to the 'include_view_ids' list if not empty
    if 'include_view_ids' in request.data and request.data['include_view_ids']:
        views_list = views_list.filter(id__in=request.data['include_view_ids'])

    # exclude property views limited to the 'exclude_view_ids' list if not empty
    if 'exclude_view_ids' in request.data and request.data['exclude_view_ids']:
        views_list = views_list.exclude(id__in=request.data['exclude_view_ids'])

    if ids_only:
        id_list = list(views_list.values_list('id', flat=True))
        return JsonResponse({
            'results': id_list
        })

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
    except DataError as e:
        return JsonResponse(
            {
                'status': 'error',
                'recommended_action': 'update_column_settings',
                'message': f'Error filtering - your data might not match the column settings data type: {str(e)}'
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        related_results = TaxLotProperty.serialize(
            views,
            show_columns,
            columns_from_database,
            include_related
        )
    except DataError as e:
        return JsonResponse(
            {
                'status': 'error',
                'recommended_action': 'update_column_settings',
                'message': f'Error filtering - your data might not match the column settings data type: {str(e)}'
            },
            status=status.HTTP_400_BAD_REQUEST
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
