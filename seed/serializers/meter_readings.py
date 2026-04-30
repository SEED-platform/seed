"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import OrderedDict
from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone as django_timezone
from django.utils.timezone import make_aware
from rest_framework import serializers

from seed.models import METER_READING_FIELDS, MeterReading, bulk_upsert_meter_readings

# import logging
# _log = logging.getLogger(__name__)

meter_fields = METER_READING_FIELDS


class MeterReadingBulkCreateUpdateSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        default_tz = django_timezone.get_default_timezone()
        for datum in data:
            datum["start_time"] = make_aware(datetime.fromisoformat(datum["start_time"]), timezone=default_tz)
            datum["end_time"] = make_aware(datetime.fromisoformat(datum["end_time"]), timezone=default_tz)
        return data

    def create(self, validated_data) -> list[MeterReading]:
        return bulk_upsert_meter_readings(MeterReading(**datum) for datum in validated_data)

    def validate(self, data):
        # duplicate start and end date pairs will cause sql errors
        date_pairs = set()
        for datum in data:
            date_pair = (datum.get("start_time"), datum.get("end_time"))
            if date_pair in date_pairs:
                raise ValidationError("Error: Each reading must have a unique combination of start_time end end_time.")
            date_pairs.add(date_pair)

        return data


class MeterReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MeterReading
        exclude = ("meter",)
        list_serializer_class = MeterReadingBulkCreateUpdateSerializer

    def _tz_aware(self, dt):
        return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

    def to_internal_value(self, data):
        default_tz = django_timezone.get_default_timezone()
        # check if the value being passed is time zone aware, if so, then error
        # because we only support non-time zone aware values
        start_time = datetime.fromisoformat(data["start_time"])
        if self._tz_aware(start_time):
            raise serializers.ValidationError({"status": "error", "message": "start_time must be non-time zone aware"})

        end_time = datetime.fromisoformat(data["end_time"])
        if self._tz_aware(end_time):
            raise serializers.ValidationError({"status": "error", "message": "end_time must be non-time zone aware"})

        data["start_time"] = make_aware(start_time, timezone=default_tz)
        data["end_time"] = make_aware(end_time, timezone=default_tz)
        return data

    def create(self, validated_data) -> MeterReading:
        return bulk_upsert_meter_readings([MeterReading(**validated_data)])[0]

    def to_representation(self, obj):
        result = OrderedDict(super().to_representation(obj))

        # TODO: we need to actually read the units from the meter, then convert accordingly.
        # SEED stores all energy data in kBtus
        result["units"] = "kBtu"
        result["id"] = obj.pk

        # put the ID first
        result.move_to_end("id", last=False)

        # do we want to convert this to a user-friendly value here?
        result["converted_value"] = obj.reading / 3.41
        result["converted_units"] = "kWh"

        return result
