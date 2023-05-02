# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import AnalysisPropertyView
from seed.serializers.analysis_output_files import AnalysisOutputFileSerializer
from seed.serializers.properties import PropertyStateSerializer


class AnalysisPropertyViewSerializer(serializers.ModelSerializer):
    output_files = AnalysisOutputFileSerializer(source='analysisoutputfile_set', many=True)
    property_state = PropertyStateSerializer()

    class Meta:
        model = AnalysisPropertyView
        fields = '__all__'
