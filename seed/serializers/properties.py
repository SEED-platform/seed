# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import (
    Property, PropertyState, PropertyView,
)


class PropertyLabelsField(serializers.RelatedField):

    def to_representation(self, value):
        return value.id


class PropertySerializer(serializers.ModelSerializer):
    # list of status labels (rather than the join field)
    labels = PropertyLabelsField(read_only=True, many=True)

    class Meta:
        model = Property


class PropertyStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PropertyState
    extra_data = serializers.JSONField()


class PropertyViewSerializer(serializers.ModelSerializer):
    state = PropertyStateSerializer()

    class Meta:
        model = PropertyView
        depth = 1
