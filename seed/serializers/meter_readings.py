"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from collections import OrderedDict
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone as django_timezone
from django.utils.timezone import make_aware
from psycopg.errors import UniqueViolation
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from seed.models import METER_READING_FIELDS, METER_READING_UPDATE_FIELDS, MeterReading, bulk_upsert_meter_readings

# import logging
# _log = logging.getLogger(__name__)

meter_fields = METER_READING_FIELDS
METER_READING_EDITABLE_FIELDS = ["start_time", "end_time", *METER_READING_UPDATE_FIELDS]
UNIQUE_VIOLATION = UniqueViolation.sqlstate


def _parse_local_meter_reading_datetime(value, field_name):
    parsed = datetime.fromisoformat(value)
    if django_timezone.is_aware(parsed):
        raise serializers.ValidationError({"status": "error", "message": f"{field_name} must be non-time zone aware"})

    return make_aware(parsed, timezone=django_timezone.get_default_timezone())


class MeterReadingBulkCreateUpdateSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        for datum in data:
            datum["start_time"] = _parse_local_meter_reading_datetime(datum["start_time"], "start_time")
            datum["end_time"] = _parse_local_meter_reading_datetime(datum["end_time"], "end_time")
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
        exclude = ("meter", "pk")
        list_serializer_class = MeterReadingBulkCreateUpdateSerializer

    def to_internal_value(self, data):
        data["start_time"] = _parse_local_meter_reading_datetime(data["start_time"], "start_time")
        data["end_time"] = _parse_local_meter_reading_datetime(data["end_time"], "end_time")
        return data

    def create(self, validated_data) -> MeterReading:
        return bulk_upsert_meter_readings([MeterReading(**validated_data)])[0]

    def update(self, instance, validated_data) -> MeterReading:
        updates = {field: validated_data[field] for field in METER_READING_EDITABLE_FIELDS if field in validated_data}
        original_pk = instance.pk
        for field, value in updates.items():
            setattr(instance, field, value)

        try:
            with transaction.atomic():
                # The reading was looked up before this transaction, so if another request has since moved or deleted
                # it, no rows match its original key. Reject the update rather than inserting the stale reading.
                if instance.pk == original_pk:
                    rows = MeterReading.objects.filter(pk=original_pk).update(**updates)
                else:
                    # start_time and end_time are part of the primary key, and TimescaleDB can't UPDATE a row's
                    # start_time into another chunk, so replace the reading instead
                    rows, _ = MeterReading.objects.filter(pk=original_pk).delete()
                    if rows:
                        instance.save(force_insert=True)
                if not rows:
                    raise NotFound({"status": "error", "message": "This meter reading was changed or deleted by another request"})
        except IntegrityError as e:
            if getattr(e.__cause__, "sqlstate", None) == UNIQUE_VIOLATION:
                message = "A reading with this start_time and end_time already exists for this meter"
            else:
                message = f"Invalid meter reading: {e}"
            raise serializers.ValidationError({"status": "error", "message": message}) from e

        return instance

    def to_representation(self, obj):
        result = OrderedDict(super().to_representation(obj))

        # TODO: we need to actually read the units from the meter, then convert accordingly.
        # SEED stores all energy data in kBtus
        result["units"] = "kBtu"
        # A reading's API id has always been its start_time, which is also the lookup in the detail URL
        result["id"] = obj.start_time

        # put the ID first
        result.move_to_end("id", last=False)

        # do we want to convert this to a user-friendly value here?
        result["converted_value"] = obj.reading / 3.41
        result["converted_units"] = "kWh"

        return result
