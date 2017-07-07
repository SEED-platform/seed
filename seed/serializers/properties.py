# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import (
    Property, PropertyState, PropertyView, PropertyMeasure
)


class PropertyLabelsField(serializers.RelatedField):
    def to_representation(self, value):
        return value.id


class PropertySerializer(serializers.ModelSerializer):
    # list of status labels (rather than the join field)
    labels = PropertyLabelsField(read_only=True, many=True)

    class Meta:
        model = Property


class PropertyMeasureSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField(source='measure.id')
    measure_id = serializers.SerializerMethodField('measure_id_name')
    name = serializers.ReadOnlyField(source='measure.name')
    display_name = serializers.ReadOnlyField(source='measure.display_name')
    category = serializers.ReadOnlyField(source='measure.category')
    category_display_name = serializers.ReadOnlyField(source='measure.category_display_name')

    class Meta:
        model = PropertyMeasure

        fields = (
            'id',
            'measure_id',
            'category',
            'name',
            'category_display_name',
            'display_name',
            'implementation_status',
        )

    def measure_id_name(self, obj):
        return "{}.{}".format(obj.measure.category, obj.measure.name)


class PropertyStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyState

    extra_data = serializers.JSONField()
    measures = PropertyMeasureSerializer(source='propertymeasure_set', many=True)


class PropertyViewSerializer(serializers.ModelSerializer):
    state = PropertyStateSerializer()

    class Meta:
        model = PropertyView
        depth = 1
