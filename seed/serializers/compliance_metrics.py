# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.utils import timezone
from rest_framework import serializers

from seed.models.compliance_metrics import ComplianceMetric
from seed.serializers.base import ChoiceField


class ComplianceMetricSerializer(serializers.ModelSerializer):
    energy_metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES, required=False)
    emission_metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES, required=False)
    organization_id = serializers.IntegerField(required=True)

    def to_representation(self, instance):
        # check for start and end date fields first
        if (self.fields['start'] == "") and (self.fields['end'] == ""):
            return
        elif self.fields['start'] == "":
            self.fields['end'] = serializers.DateTimeField(default_timezone=timezone.utc)
        elif self.fields['end'] == "":
            self.fields['start'] = serializers.DateTimeField(default_timezone=timezone.utc)
        else:
            self.fields['start'] = serializers.DateTimeField(default_timezone=timezone.utc)
            self.fields['end'] = serializers.DateTimeField(default_timezone=timezone.utc)
            return super().to_representation(instance)

    class Meta:
        model = ComplianceMetric
        fields = ('id', 'name', 'organization_id', 'start', 'end', 'actual_energy_column', 'target_energy_column', 'energy_metric_type', 'actual_emission_column', 'target_emission_column', 'emission_metric_type', 'filter_group', 'x_axis_columns',)
