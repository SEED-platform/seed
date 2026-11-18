"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db.models import Case, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import InventoryGroupMapping, Meter, MeterReading, Service, System
from seed.serializers.systems import ServiceSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger(__name__)

# `system_id` is taken from the path
service_request = AutoSchemaHelper.json_body({"name": "string", "emission_factor": "number"}, required=["name"])
meter_link = {"meter_id": "integer", "meter_alias": "string", "has_meter_data": "boolean"}


@extend_schema(
    parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.path_id_field("Inventory group ID", name="inventory_group_pk"),
        AutoSchemaHelper.path_id_field("System ID", name="system_pk"),
    ]
)
@extend_schema_view(
    create=extend_schema(request=service_request),
    update=extend_schema(request=service_request),
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
    ],
    name="create",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
    ],
    name="destroy",
)
class ServiceViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        group_pk = self.kwargs.get("inventory_group_pk")
        system_pk = self.kwargs.get("system_pk")
        return Service.objects.filter(
            system=system_pk, system__group=group_pk, system__group__organization=self.get_organization(self.request)
        )

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            # services are always saved to the path's system, which must belong to the path's group
            system = get_object_or_404(System, pk=self.kwargs["system_pk"], group=self.kwargs["inventory_group_pk"])
            kwargs["data"] = {**kwargs["data"], "system_id": system.id}
        return super().get_serializer(*args, **kwargs)

    @extend_schema(
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "id": "integer",
                    "system_name": "string",
                    "name": "string",
                    "service_meters": {"in": [meter_link], "out": [meter_link]},
                    "properties": [
                        {
                            "property_id": "integer",
                            "property_view_id": "integer",
                            "property_display_name": "string",
                            "meter_type": Meter.CONNECTION_TYPES,
                            **meter_link,
                        }
                    ],
                },
                description="service_meters are the service's Total To Users (in) and Total From Users (out) meters; "
                "properties lists the meters connecting properties to the service",
            )
        }
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    def retrieve(self, request, inventory_group_pk, system_pk, pk):
        # get service
        try:
            service = self.get_queryset().get(pk=pk)
        except Service.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "No Service matches the given query."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # get meters
        meters = Meter.objects.filter(service=pk)

        # annotate has_meter_data
        meter_ids_with_readings = MeterReading.objects.filter(meter__in=meters).values_list("meter", flat=True).distinct()
        meters = meters.annotate(has_meter_data=Case(When(id__in=meter_ids_with_readings, then=True), default=False))

        # group meters by type
        property_meters = meters.filter(property__isnull=False)
        in_meters = meters.filter(connection_type=Meter.TOTAL_TO_USERS)
        out_meters = meters.filter(connection_type=Meter.TOTAL_FROM_USERS)

        return {
            "id": service.id,
            "system_name": service.system.name,
            "name": service.name,
            "service_meters": {
                "in": [
                    {
                        "meter_id": meter.id,
                        "meter_alias": (
                            meter.alias if meter.alias else f"{meter.get_type_display()} - {meter.get_source_display()} - {meter.source_id}"
                        ),
                        "has_meter_data": meter.has_meter_data,
                    }
                    for meter in in_meters
                ],
                "out": [
                    {
                        "meter_id": meter.id,
                        "meter_alias": (
                            meter.alias if meter.alias else f"{meter.get_type_display()} - {meter.get_source_display()} - {meter.source_id}"
                        ),
                        "has_meter_data": meter.has_meter_data,
                    }
                    for meter in out_meters
                ],
            },
            "properties": [
                {
                    "property_id": meter.property_id,
                    "property_view_id": meter.property.views.first().id,
                    "property_display_name": meter.property.views.first().state.default_display_value(),
                    "meter_id": meter.id,
                    "meter_alias": (
                        meter.alias if meter.alias else f"{meter.get_type_display()} - {meter.get_source_display()} - {meter.source_id}"
                    ),
                    "meter_type": dict(Meter.CONNECTION_TYPES).get(meter.connection_type),
                    "has_meter_data": meter.has_meter_data,
                }
                for meter in property_meters
            ],
        }

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "property_ids": {"type": "array", "items": {"type": "integer"}, "description": "IDs of properties in the group"},
                    "direction": {"type": "string", "enum": ["imported", "exported"]},
                    "type": AutoSchemaHelper.schema_factory(Meter.ENERGY_TYPES),
                },
                "required": ["property_ids", "direction", "type"],
            }
        },
        responses={200: OpenApiResponse(description="Creates a meter connecting each property to the service; the body is `null`")},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def create_meters(self, request, inventory_group_pk, system_pk, pk):
        # setting source to Manual Entry to match inventory_groups system create meters
        property_ids = request.data.get("property_ids")
        direction = request.data.get("direction")
        type = request.data.get("type")

        if not (property_ids and direction and type):
            missing_args = [name for name in ("property_ids", "direction", "type") if not request.data.get(name)]
            return JsonResponse(
                {
                    "status": "error",
                    "errors": f"Missing required arg(s): {missing_args}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if type not in Meter.type_lookup:
            return JsonResponse(
                {"status": "error", "errors": f"type must be one of these: {list(Meter.type_lookup)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # the service must be in the path's system and group, and the properties must be in the group
        group_property_ids = InventoryGroupMapping.objects.filter(group=inventory_group_pk, property__in=property_ids).values_list(
            "property_id", flat=True
        )
        if not self.get_queryset().filter(pk=pk).exists() or set(property_ids) - set(group_property_ids):
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        for property_id in property_ids:
            Meter.objects.create(
                property_id=property_id,
                type=Meter.type_lookup[type],
                service_id=pk,
                source=Meter.MANUAL_ENTRY,
                connection_type=Meter.RECEIVING_SERVICE if direction == "imported" else Meter.RETURNING_TO_SERVICE,
            )
