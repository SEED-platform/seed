# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import Analysis
from seed.serializers.utils import CustomChoicesField


class AnalysisSerializer(serializers.ModelSerializer):
    service = CustomChoicesField(Analysis.SERVICE_TYPES)
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = Analysis
        fields = '__all__'
