"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import AggregateMeterSystem, BatterySystem, DESSystem, EVSESystem, System
from seed.serializers.systems import (
    AggregateMeterSystemSerializer,
    BatterySystemSerializer,
    DESSystemSerializer,
    EVSESystemSerializer,
    SystemSerializer,
)
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper

logger = logging.getLogger(__name__)

type_by_class = {
    DESSystem: "DES",
    EVSESystem: "EVSE",
    BatterySystem: "Battery",
    AggregateMeterSystem: "Aggregate Meter",
}

class_by_type = {
    "DES": DESSystem,
    "EVSE": EVSESystem,
    "Battery": BatterySystem,
    "Aggregate Meter": AggregateMeterSystem,
}

serializer_by_class = {
    DESSystem: DESSystemSerializer,
    EVSESystem: EVSESystemSerializer,
    BatterySystem: BatterySystemSerializer,
    AggregateMeterSystem: AggregateMeterSystemSerializer,
}


TYPE_SPECIFIC_FIELDS = (
    "DES: des_type, heating_capacity and/or cooling_capacity, count; EVSE: evse_type, power, voltage, count; "
    "Battery: efficiency, power_capacity, energy_capacity, voltage; Aggregate Meter: none"
)
SYSTEM_FIELDS = {
    "name": "string",
    "type": tuple(type_by_class.items()),
    "des_type": DESSystem.DES_TYPES,
    "heating_capacity": "number",
    "cooling_capacity": "number",
    "count": "integer",
    "evse_type": EVSESystem.EVSE_TYPES,
    "power": "number",
    "voltage": "number",
    "efficiency": "number",
    "power_capacity": "number",
    "energy_capacity": "number",
}
# as returned by `SystemSerializer`
SYSTEM_SCHEMA = AutoSchemaHelper.schema_factory(
    {
        "id": "integer",
        "group_id": "integer",
        **SYSTEM_FIELDS,
        "mode": "string",
        "services": [{"id": "integer", "name": "string", "emission_factor": "number", "properties": "object"}],
    },
    description=f"Type-specific fields are only included for their type ({TYPE_SPECIFIC_FIELDS}); DES systems also include mode",
)


def _success_schema(data_schema):
    return {"type": "object", "properties": {"status": {"type": "string", "enum": ["success"]}, "data": data_schema}}


def _invalid_type_response():
    return JsonResponse(
        {
            "status": "error",
            "errors": f"type must one of these: {list(class_by_type.keys())}",
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@extend_schema(
    parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.path_id_field("Inventory group ID", name="inventory_group_pk"),
    ]
)
class SystemViewSet(viewsets.ViewSet, OrgMixin):
    @extend_schema(responses={200: _success_schema({"type": "array", "items": SYSTEM_SCHEMA})})
    @method_decorator(
        [
            has_perm("requires_viewer"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    def list(self, request, inventory_group_pk):
        systems = System.objects.filter(group_id=inventory_group_pk).select_subclasses()

        return JsonResponse(
            {"status": "success", "data": SystemSerializer(systems, many=True).data},
            status=status.HTTP_200_OK,
        )

    @extend_schema(parameters=[AutoSchemaHelper.path_id_field("System ID")], responses={204: None})
    @method_decorator(
        [
            has_perm("requires_member"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    def destroy(self, request, inventory_group_pk, pk):
        org_id = self.get_organization(request)
        try:
            system = System.objects.get(pk=pk, group=inventory_group_pk, group__organization=org_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        system.delete()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("System ID")],
        request=AutoSchemaHelper.json_body(
            SYSTEM_FIELDS,
            required=["type"],
            description=f"Partial update; type must be the system's current type. Type-specific fields: {TYPE_SPECIFIC_FIELDS}",
        ),
        responses={200: SYSTEM_SCHEMA},
    )
    @method_decorator(
        [
            has_perm("requires_member"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    def update(self, request, inventory_group_pk, pk):
        org_id = self.get_organization(request)
        SystemClass = class_by_type.get(request.data.get("type"))
        if not SystemClass:
            return _invalid_type_response()
        try:
            system = SystemClass.objects.get(pk=pk, group=inventory_group_pk, group__organization=org_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        SerializerClass = serializer_by_class[SystemClass]
        # systems stay in the group validated in has_hierarchy_access
        serializer = SerializerClass(system, {**request.data, "group_id": inventory_group_pk}, partial=True)

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        system = serializer.save()
        data = SystemSerializer(system).data
        return JsonResponse(data)

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            SYSTEM_FIELDS, required=["name", "type"], description=f"Type-specific fields: {TYPE_SPECIFIC_FIELDS}"
        ),
        responses={201: _success_schema(SYSTEM_SCHEMA)},
    )
    @method_decorator(
        [
            has_perm("can_modify_data"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    def create(self, request, inventory_group_pk):
        data = request.data
        data["group_id"] = inventory_group_pk  # validated in has_hierarchy_access

        # check type
        Type = class_by_type.get(request.data.get("type"))
        if not Type:
            return _invalid_type_response()

        # validate with concrete class's serializer
        SerializerClass = serializer_by_class[Type]
        serializer = SerializerClass(data=request.data)
        if not serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # create system
        try:
            system = serializer.save()
        except IntegrityError as e:
            return JsonResponse(
                {
                    "status": "error",
                    "errors": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = SystemSerializer(system).data
        return JsonResponse({"status": "success", "data": data}, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={
            200: _success_schema(
                {
                    "type": "object",
                    "additionalProperties": {"type": "array", "items": SYSTEM_SCHEMA},
                    "description": 'Systems keyed by type, or by "DES - <mode>" for DES systems',
                }
            )
        }
    )
    @method_decorator(
        [
            has_perm("requires_viewer"),
            has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def systems_by_type(self, request, inventory_group_pk):
        """returns dictionary of systems grouped by type"""
        systems = System.objects.filter(group_id=inventory_group_pk).select_subclasses()
        typed_systems = defaultdict(list)
        systems_data = SystemSerializer(systems, many=True).data

        for system in systems_data:
            key = system["type"]
            if mode := system.get("mode"):
                key = f"{key} - {mode}"

            typed_systems[key].append(system)

        return JsonResponse(
            {"status": "success", "data": typed_systems},
            status=status.HTTP_200_OK,
        )
