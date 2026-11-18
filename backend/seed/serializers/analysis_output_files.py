"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import AnalysisOutputFile


class AnalysisOutputFileSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField(source="get_content_type_display")

    class Meta:
        model = AnalysisOutputFile
        fields = "__all__"
