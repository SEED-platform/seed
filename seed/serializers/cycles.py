# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import Cycle


class CycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cycle
        fields = ('name', 'start', 'end', 'organization', 'user', 'id',)
        extra_kwargs = {
            'user': {'read_only': True},
            'organization': {'read_only': True}
        }
