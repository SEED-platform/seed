# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers

from seed.models import UbidModel


class UbidModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = UbidModel
        fields = '__all__'

    def validate(self, data):
        has_property = 'property' in data
        has_taxlot = 'taxlot' in data
        if has_property == has_taxlot:
            raise serializers.ValidationError('A UBID must have either a Property or Taxlot id')
        return data
