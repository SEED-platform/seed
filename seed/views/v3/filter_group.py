"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin
)

from seed.decorators import ajax_request_class
from seed.models import (
    VIEW_LIST_INVENTORY_TYPE,
    VIEW_LIST_PROPERTY,
    Column,
    DataLogger,
    FilterGroup,
    Organization,
    PropertyView,
    TaxLotView
)
from seed.search import build_view_filters_and_sorts
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param


def _get_inventory_type_int(inventory_type: str) -> int:
    return next(k for k, v in VIEW_LIST_INVENTORY_TYPE if v == inventory_type)


class FilterGroupViewSet(viewsets.ViewSet, OrgMixin):

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    def create(self, request):
        org_id = self.get_organization(request)

        body = dict(request.data)
        name = body.get('name')
        inventory_type = body.get('inventory_type')
        inventory_type_int = None if inventory_type is None else _get_inventory_type_int(inventory_type)
        query_dict = body.get('query_dict', {})

        filter_group = FilterGroup(
            name=name,
            organization_id=org_id,
            inventory_type=inventory_type_int,
            query_dict=query_dict,

        )

        filter_group.save()

        return {
            "name": filter_group.name,
            "organization_id": filter_group.organization_id,
            "inventory_type": VIEW_LIST_INVENTORY_TYPE[filter_group.inventory_type][1],
            "query_dict": filter_group.query_dict,
        }

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    def retrieve(self, request, pk=None):

        filter_group = FilterGroup.objects.get(pk=pk)

        return JsonResponse({
            "name": filter_group.name,
            "organization_id": filter_group.organization_id,
            "inventory_type": VIEW_LIST_INVENTORY_TYPE[filter_group.inventory_type][1],
            "query_dict": filter_group.query_dict,
        })

    def get_inventory(filter_group: FilterGroup):
        inventory_type = filter_group.inventory_type
        org_id = filter_group.organization.id

        if inventory_type == 'property':
            views_list = (
                PropertyView.objects.select_related('property', 'state', 'cycle')
                .filter(property__organization_id=org_id)
            )
        elif inventory_type == 'taxlot':
            views_list = (
                TaxLotView.objects.select_related('taxlot', 'state', 'cycle')
                .filter(taxlot__organization_id=org_id)
            )

        # Retrieve all the columns that are in the db for this organization
        columns_from_database = Column.retrieve_all(
            org_id=org_id,
            inventory_type=inventory_type,
            only_used=False,
        )

        filters, annotations, order_by = build_view_filters_and_sorts(
            filter_group.get_query_dict(),
            columns_from_database
        )

        return views_list.annotate(**annotations).filter(filters).order_by(*order_by)
