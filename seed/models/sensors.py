# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""
from django.db import models
from seed.models import Property


class Sensor(models.Model):
    sensor_property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='sensors',
    )

    display_name = models.CharField(unique=True, max_length=255)
    location_identifier = models.CharField(max_length=2047, default="")
    description = models.CharField(max_length=2047, default="")

    sensor_type = models.CharField(max_length=63)
    units = models.CharField(max_length=63)

    column_name = models.CharField(unique=True, max_length=255)
