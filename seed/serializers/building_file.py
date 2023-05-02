# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Nicholas Long <nicholas.long@nrel.gov>
"""
from rest_framework import serializers

from seed.models import BuildingFile
from seed.serializers.base import ChoiceField


class BuildingFileSerializer(serializers.ModelSerializer):
    file_type = ChoiceField(choices=BuildingFile.BUILDING_FILE_TYPES)
    organization_id = serializers.IntegerField(allow_null=True, read_only=True)

    class Meta:
        model = BuildingFile
        fields = '__all__'
