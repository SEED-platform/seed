# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import logging
from rest_framework import serializers

from seed.models.data_views import DataView, DataViewParameter

class DataViewParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataViewParameter
        fields = '__all__'
        read_only_fields = ['data_view']

class DataViewSerializer(serializers.ModelSerializer):

    parameters = DataViewParameterSerializer(many=True)
    class Meta:
        model = DataView
        fields = ['id', 'cycles', 'filter_group', 'name', 'organization', 'parameters']
        # fields = '__all__'

    def create(self, validated_data):
        cycles = validated_data.pop('cycles')
        parameters = validated_data.pop('parameters')
        data_view = DataView.objects.create(**validated_data)
        data_view.cycles.set(cycles)

        for parameter in parameters:
            DataViewParameter.objects.create(data_view=data_view, **parameter)

        data_view.save()
        return data_view