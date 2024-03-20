# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import AnalysisPropertyView
from seed.serializers.analysis_output_files import AnalysisOutputFileSerializer


class AnalysisPropertyViewSerializer(serializers.ModelSerializer):
    output_files = AnalysisOutputFileSerializer(source='analysisoutputfile_set', many=True)
    display_name = serializers.CharField(required=False)

    class Meta:
        model = AnalysisPropertyView
        fields = '__all__'
