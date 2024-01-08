# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from typing import Tuple

import dateutil.parser
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils.timezone import make_aware
from psycopg2.extras import execute_values
from pytz import timezone
from rest_framework import serializers

from config.settings.common import TIME_ZONE
from seed.models import MeterReading

# import logging
# _log = logging.getLogger(__name__)

meter_fields = ['meter_id', 'start_time', 'end_time', 'reading', 'source_unit', 'conversion_factor']


class MeterReadingBulkCreateUpdateSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        for datum in data:
            datum['start_time'] = make_aware(dateutil.parser.parse(
                datum['start_time']), timezone=timezone(TIME_ZONE))
            datum['end_time'] = make_aware(dateutil.parser.parse(
                datum['end_time']), timezone=timezone(TIME_ZONE))
        return data

    def create(self, validated_data) -> list[MeterReading]:
        upsert_sql = (
            f"INSERT INTO seed_meterreading({', '.join(meter_fields)}) "
            'VALUES %s '
            'ON CONFLICT (meter_id, start_time, end_time) '
            'DO UPDATE SET reading=excluded.reading, source_unit=excluded.source_unit, conversion_factor=excluded.conversion_factor '
            f"RETURNING {', '.join(meter_fields)}"
        )

        with connection.cursor() as cursor:
            results: list[Tuple] = execute_values(
                cursor,
                upsert_sql,
                validated_data,
                template='(%(meter_id)s, %(start_time)s, %(end_time)s, %(reading)s, %(source_unit)s, %(conversion_factor)s)',
                fetch=True
            )

        # Convert list of tuples to list of MeterReadings for response
        updated_readings = list(map(lambda result: MeterReading(**{field: result[i] for i, field in enumerate(meter_fields)}), results))

        return updated_readings

    def validate(self, data):
        # duplicate start and end date pairs will cause sql errors
        date_pairs = set()
        for datum in data:
            date_pair = (datum.get('start_time'), datum.get('end_time'))
            if date_pair in date_pairs:
                raise ValidationError('Error: Each reading must have a unique combination of start_time end end_time.')
            date_pairs.add(date_pair)

        return data


class MeterReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeterReading
        exclude = ('meter', )
        list_serializer_class = MeterReadingBulkCreateUpdateSerializer

    def _tz_aware(self, dt):
        return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

    def to_internal_value(self, data):
        # check if the value being passed is time zone aware, if so, then error
        # because we only support non-time zone aware values
        start_time = dateutil.parser.parse(data['start_time'])
        if self._tz_aware(start_time):
            raise serializers.ValidationError({'status': 'error', 'message': 'start_time must be non-time zone aware'})

        end_time = dateutil.parser.parse(data['end_time'])
        if self._tz_aware(end_time):
            raise serializers.ValidationError({'status': 'error', 'message': 'end_time must be non-time zone aware'})

        data['start_time'] = make_aware(start_time, timezone=timezone(TIME_ZONE))
        data['end_time'] = make_aware(end_time, timezone=timezone(TIME_ZONE))
        return data

    def create(self, validated_data) -> MeterReading:
        # Can't use update_or_insert here due to manually setting the primary key for timescale
        upsert_sql = (
            f"INSERT INTO seed_meterreading({', '.join(meter_fields)}) "
            'VALUES (%(meter_id)s, %(start_time)s, %(end_time)s, %(reading)s, %(source_unit)s, %(conversion_factor)s) '
            'ON CONFLICT (meter_id, start_time, end_time) DO UPDATE '
            'SET reading=excluded.reading, source_unit=excluded.source_unit, conversion_factor=excluded.conversion_factor '
            f"RETURNING {', '.join(meter_fields)}"
        )

        with connection.cursor() as cursor:
            cursor.execute(upsert_sql, validated_data)
            result: Tuple = cursor.fetchone()

        # Convert tuple to MeterReading for response
        updated_reading = MeterReading(**{field: result[i] for i, field in enumerate(meter_fields)})
        return updated_reading

    def to_representation(self, obj):
        result = super().to_representation(obj)

        # TODO: we need to actually read the units from the meter, then convert accordingly.
        # SEED stores all energy data in kBtus
        result['units'] = 'kBtu'
        result['id'] = obj.pk

        # put the ID first
        result.move_to_end('id', last=False)

        # do we want to convert this to a user-friendly value here?
        result['converted_value'] = obj.reading / 3.41
        result['converted_units'] = 'kWh'

        return result
