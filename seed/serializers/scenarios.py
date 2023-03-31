# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import Scenario
from seed.serializers.base import ChoiceField
from seed.serializers.measures import PropertyMeasureSerializer


class ScenarioSerializer(serializers.ModelSerializer):
    measures = PropertyMeasureSerializer(many=True)
    temporal_status = ChoiceField(choices=Scenario.TEMPORAL_STATUS_TYPES)

    class Meta:
        model = Scenario
        fields = '__all__'
