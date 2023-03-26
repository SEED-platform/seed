# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.data_importer.utils import usage_point_id
from seed.models import Meter, Scenario
from seed.serializers.base import ChoiceField
from seed.utils.api import OrgMixin


class MeterSerializer(serializers.ModelSerializer, OrgMixin):
    type = ChoiceField(choices=Meter.ENERGY_TYPES, required=True)
    alias = serializers.CharField(required=False, allow_blank=True)
    source = ChoiceField(choices=Meter.SOURCES)
    source_id = serializers.CharField(required=False, allow_blank=True)
    scenario_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Meter
        exclude = ('property', 'scenario',)

    def validate_scenario_id(self, scenario_id):
        # validate that the user has access to the scenario
        if scenario_id is not None:
            org = self.get_organization(self.context['request'])
            try:
                Scenario.objects.get(property_state__organization=org, pk=scenario_id)
            except Scenario.DoesNotExist:
                raise serializers.ValidationError({'status': 'error', 'message': 'Permission error assigning scenario to meter'})

        return scenario_id

    def to_representation(self, obj):
        result = super().to_representation(obj)

        if obj.source == Meter.GREENBUTTON:
            result['source_id'] = usage_point_id(obj.source_id)

        result['scenario_name'] = obj.scenario.name if obj.scenario else None

        if obj.alias is None or obj.alias == '':
            result['alias'] = f"{obj.get_type_display()} - {obj.get_source_display()} - {result['source_id']}"

        return result
