# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Nicholas Long <nicholas.long@nrel.gov>
"""
from rest_framework import serializers

from seed.models import AuditTemplateConfig



class AuditTemplateConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditTemplateConfig
        fields = '__all__'
