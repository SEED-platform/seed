# !/usr/bin/env python

import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import response, status
from rest_framework.decorators import action

from seed.filters import ColumnListProfileFilterBackend
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import AccessLevelInstance, InventoryGroup, Meter, Organization, PropertyView
from seed.serializers.inventory_groups import InventoryGroupSerializer
from seed.serializers.meters import MeterSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.meters import PropertyMeterReadingsExporter, update_meter_connection
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

logger = logging.getLogger()


@method_decorator(name="list", decorator=[swagger_auto_schema_org_query_param, has_perm_class("requires_viewer")])
@method_decorator(name="create", decorator=[swagger_auto_schema_org_query_param, has_perm_class("requires_member")])
@method_decorator(name="update", decorator=[swagger_auto_schema_org_query_param, has_perm_class("requires_member")])
class InventoryGroupViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    serializer_class = InventoryGroupSerializer
    model = InventoryGroup
    filter_backends = (ColumnListProfileFilterBackend,)
    pagination_class = None

    def get_queryset(self):
        groups = InventoryGroup.objects.filter(organization=self.get_organization(self.request))

        access_level_instance_id = getattr(self.request, "access_level_instance_id", None)
        if access_level_instance_id:
            access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
            groups = groups.filter(
                access_level_instance__lft__gte=access_level_instance.lft, access_level_instance__rgt__lte=access_level_instance.rgt
            )

        selected = self.request.data.get("selected")
        if selected:
            groups = groups.filter(group_mappings__property_id__in=selected).distinct()

        return groups.order_by("name").distinct()

    def _get_taxlot_groups(self, request):
        qs = self.get_queryset()
        results = [InventoryGroupSerializer(q).data for q in qs]
        status_code = status.HTTP_200_OK
        return response.Response(results, status=status_code)

    def _get_property_groups(self, request):
        qs = self.get_queryset()  # ALL groups from org
        serializer_kwargs = {"instance": qs, "many": True}

        results = InventoryGroupSerializer(**serializer_kwargs).data
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

        return JsonResponse(
            {
                "status": "success",
                "data": data,
            }
        )

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @action(detail=True, methods=["POST"])
    def meter_usage(self, request, pk):
        """
        Returns meter usage for a group
        """
        try:
            group = InventoryGroup.objects.get(pk=pk)
            group = InventoryGroupSerializer(group).data
            # ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id) # ?
            org_id = self.get_organization(request)
            interval = request.data.get("interval", "Exact")
        except ObjectDoesNotExist:
            return [], JsonResponse({"status": "erorr", "message": "No such resource."})

        data = {"column_defs": [], "readings": []}
        for property_id in group["inventory_list"]:
            property_view = PropertyView.objects.filter(property=property_id).first()
            scenario_ids = [s.id for s in property_view.state.scenarios.all()]
            exporter = PropertyMeterReadingsExporter(property_id, org_id, [], scenario_ids=scenario_ids)
            usage = exporter.readings_and_column_defs(interval)
            data["readings"].extend(usage["readings"])
            data["column_defs"].extend(usage["column_defs"])

        # Remove duplicate dicts by converting to a set of tuples, then back to dicts
        data["column_defs"] = [dict(t) for t in {tuple(d.items()) for d in data["column_defs"]}]

        return JsonResponse({"status": "success", "data": data})


class InventoryGroupMetersViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    model = Meter
    serializer_class = MeterSerializer

    def get_queryset(self):
        inventory_group_pk = self.kwargs.get("inventory_group_pk", None)

        try:
            group = InventoryGroup.objects.get(pk=inventory_group_pk)
            group = InventoryGroupSerializer(group).data
        except ObjectDoesNotExist:
            return [], JsonResponse({"status": "erorr", "message": "No such resource."})

        # taxlots do not support meters
        if group["inventory_type"] != "Property":
            return [], JsonResponse({"stauts": "success", "data": []})

        return Meter.objects.filter(
            Q(property_id__in=group["inventory_list"]) | Q(system__group_id=inventory_group_pk),
        )

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def list(self, request, inventory_group_pk):
        """
        Return meters for a group
        """
        meters = self.get_queryset()
        data = MeterSerializer(meters, many=True).data

        return JsonResponse({"status": "success", "data": data})

    @action(detail=True, methods=["PUT"])
    @has_perm_class("can_modify_data")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def update_connection(self, request, inventory_group_pk, pk):
        meter = self.get_queryset().filter(pk=pk).first()
        meter_config = request.data.get("meter_config")

        try:
            update_meter_connection(meter, meter_config)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({}, status=status.HTTP_200_OK)
