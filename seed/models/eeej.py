# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging

from django.contrib.gis.db import models as geomodels
from django.db import models

logger = logging.getLogger(__name__)


class HousingType(models.TextChoices):
    PUBLIC_HOUSING = 'public housing development'
    MULTIFAMILY = 'multi-family assisted property'


class EeejCejst(models.Model):
    # Stores subset of CEJST data
    census_tract_geoid = models.CharField(max_length=11, unique=True)
    dac = models.BooleanField()
    energy_burden_low_income = models.BooleanField()
    energy_burden_percent = models.FloatField(null=True, blank=True)


class EeejHud(models.Model):
    # Stores subset of HUD data
    hud_object_id = models.CharField(max_length=20, unique=True)
    census_tract_geoid = models.CharField(max_length=11)
    long_lat = geomodels.PointField(geography=True)
    housing_type = models.CharField(max_length=100, choices=HousingType.choices)
    name = models.CharField(max_length=150)
