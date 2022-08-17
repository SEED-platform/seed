# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models.data_views import DataView


class DataViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataView
        fields = '__all__'

    def create(self, validated_data):
        columns = validated_data.pop('columns')
        cycles = validated_data.pop('cycles')

        data_view = DataView.objects.create(**validated_data)

        data_view.columns.set(columns)
        data_view.cycles.set(cycles)
        data_view.save()
        return data_view