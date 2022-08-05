# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models.data_views import DataView
from seed.serializers.columns import ColumnSerializer
from seed.serializers.cycles import CycleSerializer
from seed.serializers.data_aggregations import DataAggregationSerializer


class DataViewSerializer(serializers.ModelSerializer):
    # columns = ColumnSerializer(many=True)
    # cycles = CycleSerializer(many=True)
    # data_aggregations = DataAggregationSerializer(many=True)
    class Meta:
        model = DataView
        fields = '__all__'
        # fields = ['name', 'organization', 'filter_group']

    def create(self, validated_data):
        columns = validated_data.pop('columns')
        cycles = validated_data.pop('cycles')
        data_aggregations = validated_data.pop('data_aggregations')
        
        data_view = DataView.objects.create(**validated_data)
        
        data_view.columns.set(columns)
        data_view.cycles.set(cycles)
        data_view.data_aggregations.set(data_aggregations)
        data_view.save()
        return data_view
