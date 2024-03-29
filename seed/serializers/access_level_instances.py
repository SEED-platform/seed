# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import AccessLevelInstance


class AccessLevelInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLevelInstance
        fields = '__all__'
