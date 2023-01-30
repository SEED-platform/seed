# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import dateutil.parser
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.utils.timezone import make_aware
from pytz import timezone
from rest_framework import serializers

from config.settings.common import TIME_ZONE
from seed.models import MeterReading

# import logging
# _log = logging.getLogger(__name__)


class MeterReadingBulkCreateUpdateSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        for datum in data:
            datum['start_time'] = make_aware(dateutil.parser.parse(
                datum['start_time']), timezone=timezone(TIME_ZONE))
            datum['end_time'] = make_aware(dateutil.parser.parse(
                datum['end_time']), timezone=timezone(TIME_ZONE))
        return data

    def create(self, validated_data):
        meter_data = [MeterReading(**item) for item in validated_data]

        try:
            # Presently update_conflicts are not supported in Django 3.x.
            # An older github patch has happened, but we need to evaluate
            # it: https://github.com/martinphellwig/django-query-signals/commit/a3ed59614287f1ef9e7398d325a8bbcc11bf0b3c.
            # For now, if there is a conflict with the date/times, then it will
            # ignore the conflict and not update the reading values.
            #   update_conflicts=True,
            #   update_fields=['reading', 'source_unit', 'conversion_factor'],
            result = MeterReading.objects.bulk_create(meter_data, ignore_conflicts=True)
        except IntegrityError as e:
            raise ValidationError(e)

        return result


class MeterReadingSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        data['start_time'] = make_aware(dateutil.parser.parse(
            data['start_time']), timezone=timezone(TIME_ZONE))
        data['end_time'] = make_aware(dateutil.parser.parse(
            data['end_time']), timezone=timezone(TIME_ZONE))
        return data

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
