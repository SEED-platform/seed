# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import AnalysisRun

class AnalysisRunsSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField('get_readable_status')

    class Meta:
        model = AnalysisRun
        fields = '__all__'

    def get_readable_status(self, obj):
        return AnalysisRun.RUN_STATUSES[next((i for i, v in enumerate(AnalysisRun.RUN_STATUSES) if v[0] == obj.status), None)][1]
