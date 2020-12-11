# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import AnalysisPropertyView
from seed.serializers.analysis_output_files import AnalysisOutputFileSerializer


class AnalysisPropertyViewSerializer(serializers.ModelSerializer):
    output_files = AnalysisOutputFileSerializer(source='get_output_files', many=True)


    class Meta:
        model = AnalysisPropertyView
        fields = '__all__'
