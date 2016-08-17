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

class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property


class PropertyStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyState
    extra_data = serializers.JSONField()


class PropertyViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyView
        depth = 1
