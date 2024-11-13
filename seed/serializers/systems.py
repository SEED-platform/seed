# # !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import defaultdict

from rest_framework import serializers

from seed.data_importer.utils import usage_point_id
from seed.models import BatterySystem, DESSystem, EVSESystem, Service, System
from seed.serializers.base import ChoiceField
from seed.serializers.pint import collapse_unit


class ServiceSerializer(serializers.ModelSerializer):
    system_id = serializers.IntegerField(write_only=True)
    properties = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ["id", "name", "emission_factor", "system_id", "properties"]

    def get_properties(self, obj):
        meters_by_property = defaultdict(list)
        for meter in obj.meters.all():
            meters_by_property[meter.property_id].append(
                {
                    "alias": meter.alias
                    if meter.alias
                    else f"{meter.get_type_display()} - {meter.get_source_display()} - {usage_point_id(meter.source_id)}"
                }
            )

        return meters_by_property

    def validate(self, data):
        system_pk = data.get("system_id")
        id = self.instance.id if self.instance else None

        if Service.objects.filter(name=data.get("name"), system=system_pk).exclude(id=id).exists():
            raise serializers.ValidationError("Service name must be unique within system")
        return data


class SystemSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)
    type = serializers.ReadOnlyField(default="unknown")
    group_id = serializers.IntegerField(write_only=True)

    def to_representation(self, instance):
        if isinstance(instance, DESSystem):
            data = DESSystemSerializer(instance=instance).data
        elif isinstance(instance, EVSESystem):
            data = EVSESystemSerializer(instance=instance).data
        elif isinstance(instance, BatterySystem):
            data = BatterySystemSerializer(instance=instance).data
        else:
            raise ValueError

        data["id"] = instance.id
        data["name"] = instance.name
        data["group_id"] = instance.group.id
        data["services"] = ServiceSerializer(instance.services, many=True).data

        return data

    class Meta:
        model = System
        fields = ["id", "name", "services", "type", "group_id"]

    def validate(self, data):
        id = self.instance.id if self.instance else None

        if System.objects.filter(name=data.get("name"), group=data.get("group_id")).exclude(id=id).exists():
            raise serializers.ValidationError("System name must be unique within group")
        return data


class DESSystemSerializer(SystemSerializer):
    des_type = ChoiceField(source="type", choices=DESSystem.DES_TYPES)

    class Meta:
        model = DESSystem
        fields = [*SystemSerializer.Meta.fields, "cooling_capacity", "count", "des_type", "heating_capacity"]

    def to_representation(self, obj):
        org = obj.group.organization
        mode = "Cooling" if obj.cooling_capacity else "Heating"
        return {
            "type": "DES",
            "des_type": obj.get_type_display(),
            "cooling_capacity": collapse_unit(org, obj.cooling_capacity),
            "count": obj.count,
            "heating_capacity": collapse_unit(org, obj.heating_capacity),
            "mode": mode
        }


class EVSESystemSerializer(SystemSerializer):
    evse_type = ChoiceField(source="type", choices=EVSESystem.EVSE_TYPES)

    class Meta:
        model = EVSESystem
        fields = [*SystemSerializer.Meta.fields, "count", "evse_type", "power", "voltage"]

    def to_representation(self, obj):
        org = obj.group.organization
        return {
            "type": "EVSE",
            "evse_type": obj.get_type_display(),
            "power": collapse_unit(org, obj.power),
            "voltage": collapse_unit(org, obj.voltage),
            "count": collapse_unit(org, obj.count),
        }


class BatterySystemSerializer(SystemSerializer):
    class Meta:
        model = BatterySystem
        fields = [*SystemSerializer.Meta.fields, "energy_capacity", "power_capacity", "efficiency", "voltage"]

    def to_representation(self, obj):
        org = obj.group.organization
        return {
            "type": "Battery",
            "efficiency": obj.efficiency,
            "energy_capacity": collapse_unit(org, obj.energy_capacity),
            "power_capacity": collapse_unit(org, obj.power_capacity),
            "voltage": collapse_unit(org, obj.voltage),
        }
