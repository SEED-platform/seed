# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import AnalysisInputFile


class AnalysisInputFileSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source='get_content_type_display')

    class Meta:
        model = AnalysisInputFile
        fields = '__all__'
