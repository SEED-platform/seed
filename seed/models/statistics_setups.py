"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db import models

from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column

logger = logging.getLogger(__name__)


class StatisticsSetup(models.Model):
    # Stores all the configuration needed to calculate organization statistics
    # Retrieve default values
    # find the kbtu_thermal_conversion_factors entry under Electric that has "kWh" in it
    electric_factors = kbtu_thermal_conversion_factors("US").get("Electric", {})
    electric_default = next((item for item in electric_factors.items() if "kWh" in item), None)
    # find the value under "Natural Gas" that has "therms" in it
    gas_factors = kbtu_thermal_conversion_factors("US").get("Natural Gas", {})
    gas_default = next((item for item in electric_factors.items() if "therms" in item), None)
    # set area default to 'ft2'
    area_units_default = "ft2"
    AREA_UNITS = (
        ("ft2", "ft2"),
        ("m2", ",2"),
    )

    ELECTRIC_UNITS = (("GJ", "GJ"), ("kBtu", "kBtu"), ("kWh", "kWh"), ("MBtu/MMBtu", "MBtu/MMBtu"), ("MWh", "MWh"))

    EUI_UNITS = (
        ("kBtu/ft2", "kBtu/ft2"),
        ("kBtu/m2", "kBtu/m2"),
        ("kWh/ft2", "kWh/ft2"),
        ("kWh/m2", "kWh/m2"),
        ("GJ/m2", "GJ/m2"),
        ("GJ/ft2", "GJ/ft2"),
    )

    GAS_UNITS = (
        ("GJ", "GJ"),
        ("kBtu", "kBtu"),
        ("MBtu/MMBtu", "MBtu/MMBtu"),
        ("therms", "therms"),
        ("kWh", "kWh"),
        ("kcf", "kcf"),
        ("Mcf", "Mcf"),
    )

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    gfa_column = models.ForeignKey(Column, related_name="gfa_column", null=True, on_delete=models.SET_NULL)
    gfa_units = models.CharField(max_length=20, choices=AREA_UNITS, default=area_units_default)
    electricity_column = models.ForeignKey(Column, related_name="electricity_column", null=True, on_delete=models.SET_NULL)
    electricity_units = models.CharField(max_length=50, choices=ELECTRIC_UNITS, default=electric_default)
    natural_gas_column = models.ForeignKey(Column, related_name="natural_gas_column", null=True, on_delete=models.SET_NULL)
    natural_gas_units = models.CharField(max_length=50, choices=GAS_UNITS, default=gas_default)
    electricity_eui_column = models.ForeignKey(Column, related_name="electricity_eui_column", null=True, on_delete=models.SET_NULL)
    electricity_eui_units = models.CharField(max_length=50, choices=EUI_UNITS, default="kBtu/ft2")
    natural_gas_eui_column = models.ForeignKey(Column, related_name="natural_gas_eui_column", null=True, on_delete=models.SET_NULL)
    natural_gas_eui_units = models.CharField(max_length=50, choices=EUI_UNITS, default="kBtu/ft2")
