"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import ReportConfiguration


class ReportConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportConfiguration
        fields = ("name", "cycles", "id", "x_column", "y_column", "filter_group_id", "access_level_instance_id", "access_level_depth")
        extra_kwargs = {"user": {"read_only": True}, "organization": {"read_only": True}, "organization_id": {"read_only": True}}

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        return ret
