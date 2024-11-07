"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.data_importer.utils import usage_point_id
from seed.models import Meter, Scenario, Property
from seed.serializers.base import ChoiceField
from seed.utils.api import OrgMixin


class MeterSerializer(serializers.ModelSerializer, OrgMixin):
    type = ChoiceField(choices=Meter.ENERGY_TYPES, required=True)
    connection_type = ChoiceField(choices=Meter.CONNECTION_TYPES, required=True)
    service_id = serializers.IntegerField(source="service.id", allow_null=True, read_only=True)
    service_name = serializers.CharField(source="service.name", allow_null=True, read_only=True)
    service_group = serializers.IntegerField(source="service.system.group_id", allow_null=True, read_only=True)
    alias = serializers.CharField(required=False, allow_blank=True)
    source = ChoiceField(choices=Meter.SOURCES)
    source_id = serializers.CharField(required=False, allow_blank=True)
    property_id = serializers.IntegerField(required=False, allow_null=True)
    system_id = serializers.IntegerField(source="system.id", required=False, allow_null=True)
    system_name = serializers.CharField(source="system.name", required=False, allow_null=True)
    scenario_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Meter
        exclude = (
            "property",
            "scenario",
            "system",
            "service",
        )

    def validate_scenario_id(self, scenario_id):
        # validate that the user has access to the scenario
        if scenario_id is not None:
            org = self.get_organization(self.context["request"])
            try:
                Scenario.objects.get(property_state__organization=org, pk=scenario_id)
            except Scenario.DoesNotExist:
                raise serializers.ValidationError({"status": "error", "message": "Permission error assigning scenario to meter"})

        return scenario_id

    def to_representation(self, obj):
        result = super().to_representation(obj)
        if obj.source == Meter.GREENBUTTON:
            result["source_id"] = usage_point_id(obj.source_id)
        result["scenario_name"] = obj.scenario.name if obj.scenario else None
        if obj.alias is None or obj.alias == "":
            result["alias"] = f"{obj.get_type_display()} - {obj.get_source_display()} - {result['source_id']}"
        self.get_property_display_name(obj, result)
        self.set_config(obj, result)

        return result

    def set_config(self, obj, result):
        # generate config for meter modal
        connection_lookup = {
            1: {"direction": "inflow", "use": "outside", "connection": "outside"},
            2: {"direction": "outflow", "use": "outside", "connection": "outside"},
            3: {"direction": "inflow", "use": "using", "connection": "service"},
            4: {"direction": "outflow", "use": "using", "connection": "service"},
            5: {"direction": "inflow", "use": "offering", "connection": "service"},
            6: {"direction": "outflow", "use": "offering", "connection": "service"},
        }

        group_id, system_id = None, None
        if obj.service:
            system = obj.service.system
            group_id, system_id = system.group.id, system.id
        elif obj.system:
            group_id, system_id = obj.system.group.id, obj.system.id

        config = {"group_id": group_id, "system_id": system_id, "service_id": obj.service_id, **connection_lookup[obj.connection_type]}
        result["config"] = config

    def get_property_display_name(self, obj, result):
        if obj.property:
            state = obj.property.views.first().state
            property_display_field = state.organization.property_display_field
            result["property_display_field"] = getattr(state, property_display_field, 'Unknown')
