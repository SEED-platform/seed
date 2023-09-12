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


# make sure to add these line to the migration to import data:
""" at the top:
    from seed.lib.geospatial.eeej import add_eeej_data

    def handle_eeej_data(apps, schema_editor):
        add_eeej_data()

    and in the 'operations' list:

    migrations.RunPython(handle_eeej_data)
"""


class EeejCejst(models.Model):
    # Stores subset of CEJST data
    census_tract_geoid = models.CharField(max_length=11, unique=True)
    # Identified as disadvantaged
    dac = models.BooleanField()
    # Greater than or equal to the 90th percentile for energy burden and is low income?
    energy_burden_low_income = models.BooleanField(default=False)
    # Energy burden (percentile)
    energy_burden_percent = models.FloatField(null=True, blank=True)
    # Is low income?
    low_income = models.BooleanField(default=False)
    # Share of neighbors that are identified as disadvantaged
    share_neighbors_disadvantaged = models.FloatField(null=True, blank=True)


class EeejHud(models.Model):
    # Stores subset of HUD data
    hud_object_id = models.CharField(max_length=20, unique=True)
    census_tract_geoid = models.CharField(max_length=11)
    long_lat = geomodels.PointField(geography=True)
    housing_type = models.CharField(max_length=100, choices=HousingType.choices)
    name = models.CharField(max_length=150)
