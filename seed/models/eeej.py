# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging
from typing import Tuple

from django.contrib.gis.db import models as geomodels
from django.db import models

logger = logging.getLogger(__name__)

PUBLIC_HOUSING = 0
MULTIFAMILY = 1
HOUSING_TYPE: list[Tuple[int, str]] = [
    (PUBLIC_HOUSING, 'Public housing development'),
    (MULTIFAMILY, 'Multi-family assisted property'),
]


class EeejCejst(models.Model):
    # Stores subset of CEJST data
    census_tract_geoid = models.CharField(max_length=11, primary_key=True)
    # Identified as disadvantaged
    dac = models.BooleanField()
    # Boolean value for if a community is in the 90th percentile or greater for average annual energy cost per household ($) divided by household average income, and low income
    energy_burden_low_income = models.BooleanField()
    # Percentile of average annual energy cost per household ($) divided by household average income (0-100)
    energy_burden_percent = models.IntegerField(null=True)
    # Boolean value for if a community is in the 65th percentile or greater for percent of a census tract's population in households where household income is at or below 200% of the Federal Poverty Level
    low_income = models.BooleanField()
    # Share of neighbors that are identified as disadvantaged (0-100)
    share_neighbors_disadvantaged = models.IntegerField(null=True)


class EeejHud(models.Model):
    # Stores subset of HUD data
    hud_object_id = models.CharField(max_length=20, primary_key=True)
    census_tract_geoid = models.CharField(max_length=11)
    long_lat = geomodels.PointField(geography=True)
    housing_type = models.IntegerField(choices=HOUSING_TYPE)
    name = models.CharField(max_length=150)
