# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import Analysis


class AnalysisSerializer(serializers.ModelSerializer):
    service = serializers.SerializerMethodField('get_readable_service')
    status = serializers.SerializerMethodField('get_readable_status')

    class Meta:
        model = Analysis
        fields = '__all__'

    def get_readable_service(self, obj):
        return Analysis.SERVICE_TYPES[next((i for i, v in enumerate(Analysis.SERVICE_TYPES) if v[0] == obj.service), None)][1]

    def get_readable_status(self, obj):
        return Analysis.STATUS_TYPES[next((i for i, v in enumerate(Analysis.STATUS_TYPES) if v[0] == obj.status), None)][1]
