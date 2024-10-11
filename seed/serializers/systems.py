# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import defaultdict

from rest_framework import serializers

from seed.data_importer.utils import usage_point_id
from seed.models import BatterySystem, DESSystem, EVSESystem, Service, System
from seed.serializers.base import ChoiceField


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
        data["services"] = ServiceSerializer(instance.services, many=True).data

        return data

    class Meta:
        model = System
        fields = ["id", "name", "services", "type", "group_id"]


class DESSystemSerializer(SystemSerializer):
    DES_type = ChoiceField(source="type", choices=DESSystem.DES_TYPES)
    capacity = serializers.IntegerField()
    count = serializers.IntegerField()

    class Meta:
        model = DESSystem
        fields = [*SystemSerializer.Meta.fields, "DES_type", "capacity", "count"]

    def to_representation(self, obj):
        return {
            "type": "DES",
            "des_type": obj.get_type_display(),
            "capacity": obj.capacity,
            "count": obj.count,
        }


class EVSESystemSerializer(SystemSerializer):
    EVSE_type = ChoiceField(source="type", choices=EVSESystem.EVSE_TYPES)
    power = serializers.IntegerField()
    count = serializers.IntegerField()

    class Meta:
        model = EVSESystem
        fields = [*SystemSerializer.Meta.fields, "EVSE_type", "power", "count"]

    def to_representation(self, obj):
        return {
            "type": "EVSE",
            "evse_type": obj.get_type_display(),
            "power": obj.power,
            "count": obj.count,
        }


class BatterySystemSerializer(SystemSerializer):
    efficiency = serializers.IntegerField()
    capacity = serializers.IntegerField()
    voltage = serializers.IntegerField()

    class Meta:
        model = BatterySystem
        fields = [*SystemSerializer.Meta.fields, "efficiency", "capacity", "voltage"]

    def to_representation(self, obj):
        return {
            "type": "Battery",
            "efficiency": obj.efficiency,
            "capacity": obj.capacity,
            "voltage": obj.voltage,
        }
