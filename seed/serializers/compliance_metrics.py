# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from rest_framework import serializers

from seed.models.compliance_metrics import ComplianceMetric
from seed.serializers.base import ChoiceField


class ComplianceMetricSerializer(serializers.ModelSerializer):
    metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES)
    organization_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ComplianceMetric
        fields = ['id', 'name', 'organization_id', 'start', 'end', 'actual_column', 'target_column', 'metric_type', 'x_axis_columns']
        # fields = '__all__'
