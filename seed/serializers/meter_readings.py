# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models import MeterReading


class MeterReadingSerializer(serializers.ModelSerializer):
    # type = ChoiceField(choices=Meter.ENERGY_TYPES, required=True)
    # alias = serializers.CharField(required=False, allow_blank=True)
    # source = ChoiceField(choices=Meter.SOURCES)
    # source_id = serializers.CharField(required=False, allow_blank=True)
    # scenario_id = serializers.IntegerField(required=False, allow_null=True)
    # scenario_name = serializers.CharField(required=False, allow_blank=True)
    # # meter_readings = serializers.StringRelatedField(many=True)

    class Meta:
        model = MeterReading
        exclude = ('meter', )

    def to_representation(self, obj):
        result = super().to_representation(obj)

        # SEED stores all energy data in kBtus
        result['units'] = 'kBtu'
        result['id'] = obj.pk
        # put the ID first
        result.move_to_end('id', last=False)

        # do we want to convert this to a user friendly value here?
        result['converted_value'] = obj.reading / 3.412
        result['converted_units'] = 'kWh'

        return result
