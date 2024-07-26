# !/usr/bin/env python
# encoding: utf-8
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import response, status
from rest_framework.decorators import action

from seed.filters import ColumnListProfileFilterBackend
from seed.models import InventoryGroup, Organization, PropertyView, TaxLotView
from seed.serializers.inventory_groups import InventoryGroupSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name='create',
    decorator=swagger_auto_schema_org_query_param
)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema_org_query_param
)
class InventoryGroupViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):

    serializer_class = InventoryGroupSerializer
    model = InventoryGroup
    filter_backends = (ColumnListProfileFilterBackend,)
    pagination_class = None

    def get_queryset_for_org(self):
        groups = InventoryGroup.objects.filter(
            organization=self.get_organization(self.request)
        ).order_by("name").distinct()
        return groups

    def _get_taxlot_groups(self, request):
        qs = self.get_queryset_for_org()
        org_id = self.get_organization(self.request)

        if not self.request.data.get('selected'):
            inventory = TaxLotView.objects.filter(
                taxlot__organization_id=org_id
            ).values_list('taxlot_id', flat=True)
        else:
            inventory = TaxLotView.objects.filter(
                id__in=self.request.data.get('selected'),
                taxlot__organization_id=org_id
            ).values_list('taxlot_id', flat=True)

        results = [
            InventoryGroupSerializer(
                q,
                inventory=inventory,
                group_id=q.id,
                inventory_type=q.inventory_type
            ) for q in qs
        ]

        def member_map(group):
            group_data = group.data
            group_data['member_list'] = TaxLotView.objects.filter(
                taxlot_id__in=group.data.get('member_list')
            ).values_list('id', flat=True)
            return group_data

        results = map(member_map, results)
        status_code = status.HTTP_200_OK
        return response.Response(results, status=status_code)

    def _get_property_groups(self, request):
        qs = self.get_queryset_for_org()  # ALL groups from org
        org_id = self.get_organization(self.request)

        if not self.request.data.get('selected'):
            inventory = PropertyView.objects.filter(
                property__organization_id=org_id
            ).values_list('property_id', flat=True)
        else:
            inventory = PropertyView.objects.filter(
                id__in=self.request.data.get('selected'),
                property__organization_id=org_id
            ).values_list('property_id', flat=True)

        results = [
            InventoryGroupSerializer(
                q,
                inventory=inventory,
                group_id=q.id,
                inventory_type=q.inventory_type
            ) for q in qs
        ]

        def member_map(group):
            group_data = group.data
            group_data['member_list'] = PropertyView.objects.filter(
                property_id__in=group.data.get('member_list')
            ).values_list('id', flat=True)
            return group_data
        results = map(member_map, results)
        status_code = status.HTTP_200_OK
        return response.Response(results, status=status_code)

    @action(detail=False, methods=['POST'])
    def filter(self, request):
        # Given inventory ids, return group info & inventory ids that are in those groups
        # Request has org_id, inv_ids, inv_type
        if self.request.query_params["inventory_type"] == 'property':
            return self._get_property_groups(request)
        else:
            return self._get_taxlot_groups(request)

    def retrieve(self, request, *args, **kwargs):
        org_id = self.get_organization(self.request)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with id %s does not exist' % org_id
            }, status=status.HTTP_404_NOT_FOUND)

        groups = InventoryGroup.objects.filter(
            organization_id=org_id,
            inventory_type=request.params['inventory_type']
        )
        data = [InventoryGroupSerializer(q).data for q in groups]

        return JsonResponse({
            'status': 'success',
            'data': data,
        })
