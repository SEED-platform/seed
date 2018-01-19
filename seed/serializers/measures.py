# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

from rest_framework import serializers

from seed.models import (
    Measure,
    PropertyMeasure,
)
from seed.serializers.base import ChoiceField


class MeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Measure
        fields = '__all__'


class PropertyMeasureSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='measure.id')
    measure_id = serializers.SerializerMethodField('measure_id_name')
    name = serializers.ReadOnlyField(source='measure.name')
    display_name = serializers.ReadOnlyField(source='measure.display_name')
    category = serializers.ReadOnlyField(source='measure.category')
    category_display_name = serializers.ReadOnlyField(source='measure.category_display_name')
    implementation_status = ChoiceField(choices=PropertyMeasure.IMPLEMENTATION_TYPES)
    application_scale = ChoiceField(choices=PropertyMeasure.APPLICATION_SCALE_TYPES)
    category_affected = ChoiceField(choices=PropertyMeasure.CATEGORY_AFFECTED_TYPE)

    class Meta:
        model = PropertyMeasure

        fields = (
            'id',
            'measure_id',
            'category',
            'name',
            'category_display_name',
            'display_name',
            'category_affected',
            'application_scale',
            'recommended',
            'implementation_status',
            'cost_mv',
            'description',
            'cost_total_first',
            'cost_installation',
            'cost_material',
            'cost_capital_replacement',
            'cost_residual_value',
        )

    def measure_id_name(self, obj):
        return "{}.{}".format(obj.measure.category, obj.measure.name)
