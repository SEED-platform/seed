# !/usr/bin/env python
# encoding: utf-8

from rest_framework import serializers

from seed.models import ColumnMappingPreset


class ColumnMappingPresetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnMappingPreset
        fields = '__all__'
