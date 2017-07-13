# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""

from django.db import models

from seed.models import PropertyView, Scenario


class Meter(models.Model):
    NATURAL_GAS = 1
    ELECTRICITY = 2
    FUEL_OIL = 3
    FUEL_OIL_NO_1 = 4
    FUEL_OIL_NO_2 = 5
    FUEL_OIL_NO_4 = 6
    FUEL_OIL_NO_5_AND_NO_6 = 7
    DISTRICT_STEAM = 8
    DISTRICT_HOT_WATER = 9
    DISTRICT_CHILLED_WATER = 10
    PROPANE = 11
    LIQUID_PROPANE = 12
    KEROSENE = 13
    DIESEL = 14
    COAL = 15
    COAL_ANTHRACITE = 16
    COAL_BITUMINOUS = 17
    COKE = 18
    WOOD = 19
    OTHER = 20
    WATER = 21

    ENERGY_TYPES = (
        (NATURAL_GAS, 'Natural Gas'),
        (ELECTRICITY, 'Electricity'),
        (FUEL_OIL, 'Fuel Oil'),
        (FUEL_OIL_NO_1, 'Fuel Oil No. 1'),
        (FUEL_OIL_NO_2, 'Fuel Oil No. 2'),
        (FUEL_OIL_NO_4, 'Fuel Oil No. 4'),
        (FUEL_OIL_NO_5_AND_NO_6, 'Fuel Oil No. 5 and No. 6'),
        (DISTRICT_STEAM, 'District Steam'),
        (DISTRICT_HOT_WATER, 'District Hot Water'),
        (DISTRICT_CHILLED_WATER, 'District Chilled Water'),
        (PROPANE, 'Propane'),
        (LIQUID_PROPANE, 'Liquid Propane'),
        (KEROSENE, 'Kerosene'),
        (DIESEL, 'Diesel'),
        (COAL, 'Coal'),
        (COAL_ANTHRACITE, 'Coal Anthracite'),
        (COAL_BITUMINOUS, 'Coal Bituminous'),
        (COKE, 'Coke'),
        (WOOD, 'Wood'),
        (OTHER, 'Other'),
    )

    KILOWATT_HOURS = 1
    THERMS = 2
    WATT_HOURS = 3

    ENERGY_UNITS = (
        (KILOWATT_HOURS, 'kWh'),
        (THERMS, 'Therms'),
        (WATT_HOURS, 'Wh'),
    )

    name = models.CharField(max_length=100)
    property_view = models.ForeignKey(PropertyView, related_name='meters',
                                      on_delete=models.CASCADE, null=True, blank=True)
    scenario = models.ForeignKey(Scenario, related_name='meters',
                                      on_delete=models.CASCADE, null=True)
    energy_type = models.IntegerField(choices=ENERGY_TYPES)
    energy_units = models.IntegerField(choices=ENERGY_UNITS)


class TimeSeries(models.Model):
    """For storing energy use over time."""
    begin_time = models.DateTimeField(null=True, blank=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True, db_index=True)
    reading = models.FloatField(null=True)
    cost = models.DecimalField(max_digits=11, decimal_places=4, null=True)
    meter = models.ForeignKey(Meter, null=True, blank=True)

    class Meta:
        index_together = [['begin_time', 'end_time']]
