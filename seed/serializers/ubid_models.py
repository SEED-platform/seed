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
        if not data.get('property') and not data.get('taxlot'):
            raise serializers.ValidationError('A UBID is required to have a Property or Taxlot')
        return data
