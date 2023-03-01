# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models import AnalysisEvent, ATEvent, Event, NoteEvent
from seed.serializers.analyses import AnalysisSerializer
from seed.serializers.notes import NoteSerializer
from seed.serializers.scenarios import ScenarioSerializer


class EventSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        if isinstance(instance, ATEvent):
            return ATEventSerializer(instance=instance).data
        elif isinstance(instance, AnalysisEvent):
            return AnalysisEventSerializer(instance=instance).data
        elif isinstance(instance, NoteEvent):
            return NoteEventSerializer(instance=instance).data
        else:
            raise ValueError

    class Meta:
        model = Event
        fields = '__all__'


class ATEventSerializer(serializers.ModelSerializer):
    event_type = serializers.CharField(required=False, allow_blank=True)
    scenarios = ScenarioSerializer(many=True)

    class Meta:
        model = ATEvent
        fields = '__all__'
        extra_kwargs = {
            'user': {'read_only': True},
        }

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["event_type"] = "ATEvent"

        return result


class AnalysisEventSerializer(serializers.ModelSerializer):
    event_type = serializers.CharField(required=False, allow_blank=True)
    analysis = AnalysisSerializer()

    class Meta:
        model = AnalysisEvent
        fields = '__all__'

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["event_type"] = "AnalysisEvent"
        
        highlights = obj.analysis.get_highlights(obj.property_id)
        result["analysis"]["highlights"] = highlights

        return result


class NoteEventSerializer(serializers.ModelSerializer):
    event_type = serializers.CharField(required=False, allow_blank=True)
    note = NoteSerializer()

    class Meta:
        model = NoteEvent
        fields = '__all__'

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["event_type"] = "NoteEvent"

        return result
