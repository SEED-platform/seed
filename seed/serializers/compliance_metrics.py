# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
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
        self.fields['start'] = serializers.DateTimeField(default_timezone=timezone.utc)
        self.fields['end'] = serializers.DateTimeField(default_timezone=timezone.utc)
        return super().to_representation(instance)

    class Meta:
        model = ComplianceMetric
        fields = ('id', 'name', 'organization_id', 'start', 'end', 'actual_energy_column', 'target_energy_column', 'energy_metric_type', 'actual_emission_column', 'target_emission_column', 'emission_metric_type', 'x_axis_columns',)
