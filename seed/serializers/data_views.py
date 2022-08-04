# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from rest_framework import serializers

from seed.models.data_views import DataView
from seed.serializers.utils import CustomChoicesField


class DataViewSerializer(serializers.ModelSerializer):

    class Meta:
        model = DataView
        fields = '__all__'

    def create(self, validated_data):
        data_view = DataView.objects.create(**validated_data)
        data_view.save()
        return data_view
