# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Nicholas Long <nicholas.long@nrel.gov>
"""

from rest_framework import serializers

from seed.models import (
    BuildingFile,
)
from seed.serializers.base import ChoiceField


class BuildingFileSerializer(serializers.ModelSerializer):
    file_type = ChoiceField(choices=BuildingFile.BUILDING_FILE_TYPES)
    organization_id = serializers.IntegerField(allow_null=True, read_only=True)

    class Meta:
        model = BuildingFile
        fields = '__all__'
