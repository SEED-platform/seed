# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
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
