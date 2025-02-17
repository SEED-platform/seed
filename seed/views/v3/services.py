"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db.models import Case, When
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import Meter, MeterReading, Service
from seed.serializers.systems import ServiceSerializer
from seed.utils.api import OrgMixin
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

    @swagger_auto_schema_org_query_param
    @ajax_request_class
    @has_perm_class("can_view_data")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    def retrieve(self, request, inventory_group_pk, system_pk, pk):
        # get service
        service = Service.objects.get(pk=pk)

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
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(inventory_group_id_kwarg="inventory_group_pk")
    @action(detail=True, methods=["POST"])
    def create_meters(self, request, inventory_group_pk, system_pk, pk):
        property_ids = request.data["property_ids"]
        direction = request.data["direction"]
        type = request.data["type"]

        for property_id in property_ids:
            Meter.objects.create(
                property_id=property_id,
                type=Meter.type_lookup[type],
                service_id=pk,
                connection_type=Meter.RECEIVING_SERVICE if direction == "imported" else Meter.RETURNING_TO_SERVICE,
            ).save()
