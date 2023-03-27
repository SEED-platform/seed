# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import AnalysisEvent, ATEvent, Event, NoteEvent
from seed.serializers.analyses import AnalysisSerializer
from seed.serializers.notes import NoteSerializer
from seed.serializers.scenarios import ScenarioSerializer


class EventSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        if isinstance(instance, ATEvent):
            data = ATEventSerializer(instance=instance).data
        elif isinstance(instance, AnalysisEvent):
            data = AnalysisEventSerializer(instance=instance).data
            data['user_id'] = data['analysis']['user']
        elif isinstance(instance, NoteEvent):
            data = NoteEventSerializer(instance=instance).data
            data['user_id'] = data['note']['user_id']
        else:
            raise ValueError
        data['cycle_end_date'] = instance.cycle.end
        return data

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

        analysis_property_views = obj.analysis.get_property_view_info(obj.property_id)["views"]
        result["analysis"]["views"] = analysis_property_views

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
