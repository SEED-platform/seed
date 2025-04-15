"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import FacilitiesPlanRun


class FacilitiesPlanRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacilitiesPlanRun
        fields = "__all__"
