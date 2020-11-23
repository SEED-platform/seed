# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import Analysis

class AnalysisSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField('get_readable_type')

    class Meta:
        model = Analysis
        fields = '__all__'

    def get_readable_type(self, obj):
        return Analysis.ANALYSIS_TYPES[next((i for i, v in enumerate(Analysis.ANALYSIS_TYPES) if v[0] == obj.type), None)][1]
