"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging
from collections import defaultdict

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import BatterySystem, DESSystem, EVSESystem, System
from seed.serializers.systems import BatterySystemSerializer, DESSystemSerializer, EVSESystemSerializer, SystemSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param

logger = logging.getLogger()

type_by_class = {
    DESSystem: "DES",
    EVSESystem: "EVSE",
    BatterySystem: "Battery",
}

class_by_type = {
    "DES": DESSystem,
    "EVSE": EVSESystem,
    "Battery": BatterySystem,
}

serializer_by_class = {
    DESSystem: DESSystemSerializer,
    EVSESystem: EVSESystemSerializer,
    BatterySystem: BatterySystemSerializer,
}


class SystemViewSet(viewsets.ViewSet, OrgMixin):
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def list(self, request, inventory_group_pk):
        systems = System.objects.filter(group_id=inventory_group_pk).select_subclasses()

        return JsonResponse(
            {"status": "success", "data": SystemSerializer(systems, many=True).data},
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def destroy(self, request, inventory_group_pk, pk):
        org_id = self.get_organization(request)
        try:
            system = System.objects.get(pk=pk, group=inventory_group_pk, group__organization=org_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        system.delete()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def update(self, request, inventory_group_pk, pk):
        org_id = self.get_organization(request)
        SystemClass = class_by_type.get(request.data.get("type"))
        try:
            system = SystemClass.objects.get(pk=pk, group=inventory_group_pk, group__organization=org_id)
        except ObjectDoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        SerializerClass = serializer_by_class[SystemClass]
        serializer = SerializerClass(system, request.data, partial=True)

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

    @has_perm_class("can_modify_data")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def create(self, request, inventory_group_pk):
        data = request.data
        data["group_id"] = inventory_group_pk  # validated in has_hierarchy_access

        # check type
        Type = class_by_type.get(request.data.get("type"))
        if not Type:
            return JsonResponse(
                {
                    "status": "error",
                    "errors": f"type must one of these: {list(class_by_type.keys())}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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

    @has_perm_class("requires_viewer")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
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
