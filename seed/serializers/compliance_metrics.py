# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models.compliance_metrics import ComplianceMetric
from seed.serializers.base import ChoiceField


class ComplianceMetricSerializer(serializers.ModelSerializer):
    energy_metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES, required=False)
    emission_metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES, required=False)
    organization_id = serializers.IntegerField(required=True)

    def to_representation(self, instance):
        """Override the to_representation method to guarantee x_axis_columns sort order"""
        ret = super().to_representation(instance)
        ret['x_axis_columns'] = sorted(ret['x_axis_columns'])
        return ret

    class Meta:
        model = ComplianceMetric
        fields = ('id', 'name', 'organization_id', 'cycles', 'actual_energy_column', 'target_energy_column', 'energy_metric_type', 'actual_emission_column', 'target_emission_column', 'emission_metric_type', 'filter_group', 'x_axis_columns',)
