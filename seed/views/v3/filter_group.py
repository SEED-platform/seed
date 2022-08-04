"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status

from seed.decorators import ajax_request_class
from seed.models import (
    VIEW_LIST_INVENTORY_TYPE,
    FilterGroup,
)
from seed.serializers.filter_groups import FilterGroupSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


def _get_inventory_type_int(inventory_type: str) -> int:
    return next(k for k, v in VIEW_LIST_INVENTORY_TYPE if v == inventory_type)


@method_decorator(
    name='list',
    decorator=swagger_auto_schema_org_query_param)
@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema_org_query_param)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema_org_query_param)
@method_decorator(
    name='destroy',
    decorator=swagger_auto_schema_org_query_param)
class FilterGroupViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    model = FilterGroup
    serializer_class = FilterGroupSerializer

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    def create(self, request):
        org_id = self.get_organization(request)

        body = dict(request.data)
        name = body.get('name')
        inventory_type = body.get('inventory_type')
        query_dict = body.get('query_dict', {})

        if not name:
            return JsonResponse({
                'success': False,
                'message': 'name is missing'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not inventory_type:
            return JsonResponse({
                'success': False,
                'message': 'inventory_type is missing'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            inventory_type_int = _get_inventory_type_int(inventory_type)
        except StopIteration:
            return JsonResponse({
                'success': False,
                'message': 'invalid "inventory_type" must be "Property" or "Tax Lot"'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            filter_group = FilterGroup.objects.create(
                name=name,
                organization_id=org_id,
                inventory_type=inventory_type_int,
                query_dict=query_dict,
            )
        except IntegrityError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse(
            {
                "name": filter_group.name,
                "id": filter_group.id,
                "organization_id": filter_group.organization_id,
                "inventory_type": VIEW_LIST_INVENTORY_TYPE[filter_group.inventory_type][1],
                "query_dict": filter_group.query_dict,
            },
            status=status.HTTP_201_CREATED
        )
