# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from rest_framework import serializers

from seed.models import MeterReading


class MeterReadingBulkCreateUpdateSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        print(validated_data)
        meter_data = [MeterReading(**item) for item in validated_data]

        try:
            result = MeterReading.objects.bulk_create(meter_data)
        except IntegrityError as e:
            raise ValidationError(e)

        return result


class MeterReadingSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        instance = MeterReading(**validated_data)

        if isinstance(self._kwargs["data"], dict):
            instance.save()

        return instance

    class Meta:
        model = MeterReading
        exclude = ('meter', )
        list_serializer_class = MeterReadingBulkCreateUpdateSerializer

    def to_representation(self, obj):
        result = super().to_representation(obj)

        # SEED stores all energy data in kBtus
        result['units'] = 'kBtu'
        result['id'] = obj.pk
        # put the ID first
        result.move_to_end('id', last=False)

        # do we want to convert this to a user friendly value here?
        result['converted_value'] = obj.reading / 3.412
        result['converted_units'] = 'kWh'

        return result
