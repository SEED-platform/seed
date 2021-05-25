# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models.derived_columns import DerivedColumn, DerivedColumnParameter


class DerivedColumnParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DerivedColumnParameter
        fields = '__all__'


class DerivedColumnSerializer(serializers.ModelSerializer):
    parameters = serializers.SerializerMethodField()

    class Meta:
        model = DerivedColumn
        exclude = ['source_columns']

    def get_parameters(self, obj):
        derived_column_parameters = DerivedColumnParameter.objects.filter(derived_column=obj.id)
        return DerivedColumnParameterSerializer(derived_column_parameters, many=True).data
