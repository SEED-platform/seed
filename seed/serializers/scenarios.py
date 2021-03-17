# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers
from seed.serializers.base import ChoiceField

from seed.models import Scenario
from seed.serializers.measures import PropertyMeasureSerializer


class ScenarioSerializer(serializers.ModelSerializer):
    measures = PropertyMeasureSerializer(many=True)
    temporal_status = ChoiceField(choices=Scenario.TEMPORAL_STATUS_TYPES)

    class Meta:
        model = Scenario
        fields = '__all__'
