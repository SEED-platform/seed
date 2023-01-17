# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.data_importer.utils import usage_point_id
from seed.models import Meter
from seed.serializers.base import ChoiceField

# from seed.serializers.meter_readings import MeterReadingSerializer


class MeterSerializer(serializers.ModelSerializer):
    type = ChoiceField(choices=Meter.ENERGY_TYPES, required=True)
    alias = serializers.CharField(required=False, allow_blank=True)
    source = ChoiceField(choices=Meter.SOURCES)
    source_id = serializers.CharField(required=False, allow_blank=True)
    scenario_id = serializers.IntegerField(required=False, allow_null=True)
    scenario_name = serializers.CharField(required=False, allow_blank=True)
    # meter_readings = MeterReadingSerializer(many=True)

    class Meta:
        model = Meter
        exclude = ('property', 'scenario',)

    def to_representation(self, obj):
        result = super().to_representation(obj)

        if obj.source == Meter.GREENBUTTON:
            result['source_id'] = usage_point_id(obj.source_id)

        result['scenario_name'] = obj.scenario.name if obj.scenario else None

        if obj.alias is None or obj.alias == '':
            result['alias'] = f"{obj.get_type_display()} - {obj.get_source_display()} - {result['source_id']}"

        return result
