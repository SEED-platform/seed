"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db.models import Case, When
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import Meter, MeterReading, Service
from seed.serializers.systems import ServiceSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger()


class ServiceViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        group_pk = self.kwargs.get("inventory_group_pk")
        system_pk = self.kwargs.get("system_pk")
        return Service.objects.filter(
            system=system_pk, system__group=group_pk, system__group__organization=self.get_organization(self.request)
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
            service = Service.objects.get(system_id=system_pk, pk=pk)
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

    @swagger_auto_schema_org_query_param
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

        if not property_ids and direction and type:
            missing_args = [arg for arg in [property_ids, direction, type] if arg is None]
            return JsonResponse(
                {
                    "status": "error",
                    "errors": f"Missing required arg(s): {missing_args}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        for property_id in property_ids:
            Meter.objects.create(
                property_id=property_id,
                type=Meter.type_lookup[type],
                service_id=pk,
                source="Manual Entry",
                connection_type=Meter.RECEIVING_SERVICE if direction == "imported" else Meter.RETURNING_TO_SERVICE,
            )
