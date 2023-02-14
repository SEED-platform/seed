# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models import AnalysisEvent, ATEvent, Event
from seed.serializers.analyses import AnalysisSerializer


class EventSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        if isinstance(instance, ATEvent):
            return ATEventSerializer(instance=instance).data
        elif isinstance(instance, AnalysisEvent):
            return AnalysisEventSerializer(instance=instance).data
        else:
            raise ValueError

    class Meta:
        model = Event
        fields = '__all__'


class ATEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATEvent
        fields = '__all__'


class AnalysisEventSerializer(serializers.ModelSerializer):
    analysis = AnalysisSerializer()

    class Meta:
        model = AnalysisEvent
        fields = '__all__'
