# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Nicholas Long <nicholas.long@nrel.gov>
"""

from rest_framework import serializers

from seed.models import (
    BuildingFile,
)


class BuildingFileSerializer(serializers.ModelSerializer):
    file_type_name = serializers.SerializerMethodField()

    class Meta:
        model = BuildingFile
        fields = '__all__'

    def get_file_type_name(self, obj):
        return obj.get_file_type_display()
