# !/usr/bin/env python

import logging

from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import Count, F, Q, Sum
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.utils.timezone import make_aware
from pint import Quantity
from pytz import timezone
from rest_framework import response, status
from rest_framework.decorators import action

from config.settings.common import TIME_ZONE
from seed.filters import ColumnListProfileFilterBackend
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import AccessLevelInstance, Cycle, InventoryGroup, Meter, MeterReading, Organization, PropertyView
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
    @action(detail=True, methods=["GET"])
    @has_hierarchy_access(inventory_group_id_kwarg="pk")
    def dashboard(self, request, pk):
        cycle = Cycle.objects.get(pk=request.query_params.get("cycle_id"))

        # add view based info
        views = PropertyView.objects.filter(property__group_mappings__group=pk, cycle_id=cycle.id)
        view_data = views.aggregate(
            gross_floor_area=Sum("state__gross_floor_area"),
            site_eui=Sum("state__site_eui"),
            number_of_view=Count("id"),
            number_of_view_missing_site_eui=Count("id", filter=Q(state__site_eui__isnull=True)),
            number_of_view_missing_gross_floor_area=Count("id", filter=Q(state__gross_floor_area__isnull=True)),
        )
        if isinstance(view_data["gross_floor_area"], Quantity):
            view_data["gross_floor_area"] = int(view_data["gross_floor_area"].to_base_units().magnitude)
        if isinstance(view_data["site_eui"], Quantity):
            view_data["site_eui"] = int(view_data["site_eui"].to_base_units().magnitude)

        # calculate total export / import
        group_meters = Meter.objects.filter(Q(system__group_id=pk) | Q(property__group_mappings__group_id=pk))

        # make cycle start/end timezone aware to query MeterReading table
        the_tz = timezone(TIME_ZONE)
        start_time = make_aware(datetime.combine(cycle.start, datetime.min.time()), timezone=the_tz)
        end_time = make_aware(datetime.combine(cycle.end, datetime.min.time()), timezone=the_tz)

        importing_meters = group_meters.filter(connection_type=Meter.IMPORTED)
        importing_readings = MeterReading.objects.filter(meter__in=importing_meters, start_time__gte=start_time, end_time__lte=end_time)
        importing_total = (
            importing_readings.annotate(type=F("meter__type")).values("type").annotate(total=Sum("reading")).values("type", "total")
        )
        importing_total = {Meter.ENERGY_TYPE_BY_METER_TYPE[d["type"]]: d["total"] for d in importing_total}

        exporting_meters = group_meters.filter(connection_type=Meter.EXPORTED)
        exporting_readings = MeterReading.objects.filter(meter__in=exporting_meters, start_time__gte=start_time, end_time__lte=end_time)
        exporting_total = (
            exporting_readings.annotate(type=F("meter__type")).values("type").annotate(total=Sum("reading")).values("type", "total")
        )
        exporting_total = {Meter.ENERGY_TYPE_BY_METER_TYPE[d["type"]]: d["total"] for d in exporting_total}

        readable_data = {
            "Gross Floor Area": view_data["gross_floor_area"],
            "Site EUI": view_data["site_eui"],
            "Views Count": view_data["number_of_view"],
            "Views Missing Site EUI": view_data["number_of_view_missing_site_eui"],
            "Views Missing Gross Floor Area": view_data["number_of_view_missing_gross_floor_area"],
            "importing_total": importing_total,
            "exporting_total": exporting_total,
        }
        return JsonResponse({"status": "success", "data": readable_data})

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(inventory_group_id_kwarg="pk")
    @action(detail=True, methods=["POST"])
    def meter_usage(self, request, pk):
        """
        Returns meter usage for a group
        """
        org_id = self.get_organization(request)
        interval = request.data.get("interval", "Exact")

        meters = Meter.objects.filter(Q(system__group_id=pk) | Q(property__group_mappings__group_id=pk))
        exporter = PropertyMeterReadingsExporter(meters, org_id)
        data = exporter.readings_and_column_defs(interval)

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
            Q(service__isnull=True) | Q(service__system__group_id=inventory_group_pk),
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

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def create(self, request, inventory_group_pk):
        meter_serializer = MeterSerializer(
            data={
                **request.data,
                "connection_type": "Imported",
                "source": "Manual Entry",
            }
        )

        if not meter_serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "errors": meter_serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        meter = meter_serializer.save()
        data = MeterSerializer(meter).data
        return JsonResponse(data)
