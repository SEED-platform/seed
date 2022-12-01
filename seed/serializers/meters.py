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


class MeterSerializer(serializers.ModelSerializer):
    type = ChoiceField(choices=Meter.ENERGY_TYPES, required=True)
    source = ChoiceField(choices=Meter.SOURCES)
    source_id = serializers.CharField()
    property_id = serializers.IntegerField(required=True)
    scenario_id = serializers.IntegerField(allow_null=True, required=False)
    scenario_name = serializers.CharField(allow_blank=True, required=False)
    # meter_readings = serializers.StringRelatedField(many=True)

    class Meta:
        model = Meter
        exclude = ('property', 'scenario',)

    def to_representation(self, obj):
        result = super().to_representation(obj)

        if obj.source == Meter.GREENBUTTON:
            result['source_id'] = usage_point_id(obj.source_id)

        result['scenario_name'] = obj.scenario.name if obj.scenario else None

        return result
