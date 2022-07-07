# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models.data_aggregations import DataAggregation
from seed.serializers.utils import CustomChoicesField


class DataAggregationSerializer(serializers.ModelSerializer):
    type = CustomChoicesField(DataAggregation.AGGREGATION_TYPES)

    class Meta:
        model = DataAggregation
        fields = '__all__'

    def create(self, validated_data):
        data_aggregation = DataAggregation.objects.create(**validated_data)
        data_aggregation.save()
        return data_aggregation
