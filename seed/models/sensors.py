# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import Property


class DataLogger(models.Model):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='data_loggers',
    )

    display_name = models.CharField(max_length=255)
    identifier = models.CharField(max_length=255, default="")
    location_description = models.CharField(max_length=2047, default="")
    is_occupied_data = models.JSONField(null=False, default=dict)
    manufacturer_name = models.CharField(max_length=255, null=True)
    model_name = models.CharField(max_length=255, null=True)
    serial_number = models.CharField(max_length=255, null=True)

    class Meta:
        unique_together = ('property', 'display_name')


class Sensor(models.Model):
    data_logger = models.ForeignKey(
        DataLogger,
        on_delete=models.CASCADE,
        related_name='sensors',
    )

    display_name = models.CharField(max_length=255)
    location_description = models.CharField(max_length=2047, default="")
    description = models.CharField(max_length=2047, default="")

    sensor_type = models.CharField(max_length=63)
    units = models.CharField(max_length=63)

    column_name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('data_logger', 'display_name')
        unique_together = ('data_logger', 'column_name')


class SensorReading(models.Model):
    reading = models.FloatField(null=True)
    timestamp = models.DateTimeField()
    sensor = models.ForeignKey(
        Sensor,
        on_delete=models.CASCADE,
        related_name='sensor_readings',
    )
    is_occupied = models.BooleanField(null=False)

    class Meta:
        unique_together = ('timestamp', 'sensor')
