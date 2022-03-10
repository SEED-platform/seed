# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
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
    location_identifier = models.CharField(max_length=2047, default="")

    class Meta:
        unique_together = ('property', 'display_name')


class Sensor(models.Model):
    data_logger = models.ForeignKey(
        DataLogger,
        on_delete=models.CASCADE,
        related_name='sensors',
    )

    display_name = models.CharField(max_length=255)
    location_identifier = models.CharField(max_length=2047, default="")
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

    class Meta:
        unique_together = ('timestamp', 'sensor')
