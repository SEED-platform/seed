# !/usr/bin/env python

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import response, status
from rest_framework.decorators import action

from seed.filters import ColumnListProfileFilterBackend
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import InventoryGroup, Organization, PropertyView, TaxLotView
from seed.serializers.inventory_groups import InventoryGroupSerializer
from seed.utils.access_level_instance import access_level_filter
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet
import logging


@method_decorator(name="list", decorator=[swagger_auto_schema_org_query_param, has_perm_class("requires_viewer")])
@method_decorator(name="create", decorator=swagger_auto_schema_org_query_param)
@method_decorator(name="update", decorator=[swagger_auto_schema_org_query_param, has_perm_class("requires_member")])
class InventoryGroupViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    serializer_class = InventoryGroupSerializer
    model = InventoryGroup
    filter_backends = (ColumnListProfileFilterBackend,)
    pagination_class = None

    def get_queryset(self):
        groups = InventoryGroup.objects.filter(organization=self.get_organization(self.request))
        access_level_id = getattr(self.request, "access_level_instance_id", None)
        if access_level_id:
            groups = groups.filter(**access_level_filter(access_level_id))

        return groups.order_by("name").distinct()

    def _get_taxlot_groups(self, request):
        qs = self.get_queryset()
        results = [InventoryGroupSerializer(q).data for q in qs]
        status_code = status.HTTP_200_OK
        return response.Response(results, status=status_code)

    def _get_property_groups(self, request):
        qs = self.get_queryset()  # ALL groups from org
        results = [InventoryGroupSerializer(q).data for q in qs]
        status_code = status.HTTP_200_OK
        return response.Response(results, status=status_code)

    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["POST"])
    def filter(self, request):
        # Given inventory ids, return group info & inventory ids that are in those groups
        # Request has org_id, inv_ids, inv_type
        if self.request.query_params["inventory_type"] == "property":
            return self._get_property_groups(request)
        else:
            return self._get_taxlot_groups(request)

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    def retrieve(self, request, pk):
        org_id = self.get_organization(self.request)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "organization with id %s does not exist" % org_id}, status=status.HTTP_404_NOT_FOUND
            )

        group = InventoryGroup.objects.filter(organization_id=org.id, pk=pk).first()
        data = InventoryGroupSerializer(group).data
        # data = [InventoryGroupSerializer(q).data for q in group]

        return JsonResponse(
            {
                "status": "success",
                "data": data,
            }
        )
