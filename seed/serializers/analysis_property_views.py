# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
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
