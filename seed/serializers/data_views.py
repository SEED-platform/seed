# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import transaction
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
        fields = ['id', 'cycles', 'filter_groups', 'name', 'organization', 'parameters']
        # fields = '__all__'

    def create(self, validated_data):
        with transaction.atomic():
            cycles = validated_data.pop('cycles')
            filter_groups = validated_data.pop('filter_groups')
            parameters = validated_data.pop('parameters')
            data_view = DataView.objects.create(**validated_data)
            data_view.cycles.set(cycles)
            data_view.filter_groups.set(filter_groups)

            for parameter in parameters:
                DataViewParameter.objects.create(data_view=data_view, **parameter)

            data_view.save()
            return data_view

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance.organization = validated_data.get('organization', instance.organization)
            instance.name = validated_data.get('name', instance.name)
            if validated_data.get('filter_groups'):
                instance.filter_groups.set(validated_data['filter_groups'])
            if validated_data.get('cycles'):
                instance.cycles.set(validated_data['cycles'])

            instance.save()

            # if new parameters are provided, delete previous ones so we can create the new params
            paramters_data = validated_data.get('parameters')
            if paramters_data:
                DataViewParameter.objects.filter(data_view=instance).delete()

                for parameter in paramters_data:
                    DataViewParameter.objects.create(data_view=instance, **parameter)

            return instance
