"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status

from seed.decorators import ajax_request_class
from seed.models import VIEW_LIST_INVENTORY_TYPE, FilterGroup
from seed.models.filter_group import LABEL_LOGIC_TYPE
from seed.models.models import StatusLabel
from seed.serializers.filter_groups import FilterGroupSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


def _get_inventory_type_int(inventory_type: str) -> int:
    return next(k for k, v in VIEW_LIST_INVENTORY_TYPE if v == inventory_type)


def _get_label_logic_int(label_logic: str) -> int:
    return next(k for k, v in LABEL_LOGIC_TYPE if v == label_logic)


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
        label_logic = body.get('label_logic', "and")
        label_ids = body.get('labels', [])

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
            label_logic_int = _get_label_logic_int(label_logic)
        except StopIteration:
            return JsonResponse({
                'success': False,
                'message': 'invalid "label_logic" must be "and", "or", or "exclude"'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            filter_group = FilterGroup.objects.create(
                name=name,
                organization_id=org_id,
                inventory_type=inventory_type_int,
                query_dict=query_dict,
                label_logic=label_logic_int,
            )
        except IntegrityError as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        good_label_ids, bad_label_ids = self._get_labels(label_ids)
        filter_group.labels.add(*good_label_ids)
        filter_group.save()

        result = {
            "status": 'success',
            "data": FilterGroupSerializer(filter_group).data,
        }

        if len(bad_label_ids) > 0:
            result["warnings"] = f"labels with ids do not exist: {', '.join([str(id) for id in bad_label_ids])}"

        return JsonResponse(result, status=status.HTTP_201_CREATED)

    def _get_labels(self, label_ids):
        good_label_ids = []
        bad_label_ids = []
        for id in label_ids:
            label = StatusLabel.objects.filter(id=id)

            if label.exists():
                good_label_ids.append(id)
            else:
                bad_label_ids.append(id)

        return good_label_ids, bad_label_ids
