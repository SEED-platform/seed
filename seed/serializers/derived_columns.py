# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers
from django.db import transaction

from seed.models.derived_columns import DerivedColumn, DerivedColumnParameter
from seed.serializers.utils import CustomChoicesField


class DerivedColumnParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = DerivedColumnParameter
        fields = '__all__'
        read_only_fields = ['derived_column']


class DerivedColumnSerializer(serializers.ModelSerializer):
    parameters = DerivedColumnParameterSerializer(source='derivedcolumnparameter_set', many=True)
    inventory_type = CustomChoicesField(DerivedColumn.INVENTORY_TYPES)

    class Meta:
        model = DerivedColumn
        exclude = ['source_columns']

    def create(self, validated_data):
        parameters_data = validated_data.pop('derivedcolumnparameter_set')

        with transaction.atomic():
            derived_column = DerivedColumn.objects.create(**validated_data)

            for parameter_data in parameters_data:
                DerivedColumnParameter.objects.create(
                    derived_column=derived_column,
                    **parameter_data
                )
            return derived_column

    def update(self, instance, validated_data):
        parameters_data = validated_data.get('derivedcolumnparameter_set', [])

        with transaction.atomic():
            instance.name = validated_data.get('name', instance.name)
            instance.expression = validated_data.get('expression', instance.expression)
            instance.save()

            # if new parameters are provided, delete previous ones so we can create the new params
            if parameters_data:
                DerivedColumnParameter.objects.filter(derived_column=instance).delete()

                for param in parameters_data:
                    DerivedColumnParameter.objects.create(
                        derived_column=instance,
                        source_column=param['source_column'],
                        parameter_name=param['parameter_name'],
                    )

            return instance
