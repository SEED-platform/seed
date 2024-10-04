"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db import IntegrityError
from django.http import JsonResponse
from rest_framework import status, viewsets

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

    @has_perm_class("can_modify_data")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def create(self, request, inventory_group_pk):
        data = request.data
        data["group_id"] = inventory_group_pk  # validated in has_hierarchy_access

        logger.error("++++")
        logger.error(request.data)
        logger.error(request.data.get("type"))
        logger.error(class_by_type.get(request.data.get("type")))
        logger.error("++++")
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
            serializer.save()
        except IntegrityError as e:
            return JsonResponse(
                {
                    "status": "error",
                    "errors": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return JsonResponse({"status": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)
