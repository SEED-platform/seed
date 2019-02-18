# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""

from django.db import models

from seed.models import Property

from quantityfield.fields import QuantityField


class Meter(models.Model):
    # Previously included in model
    # ELECTRICITY = 1
    # NATURAL_GAS = 2
    # FUEL_OIL = 3
    # FUEL_OIL_NO_1 = 4
    # FUEL_OIL_NO_2 = 5
    # FUEL_OIL_NO_4 = 6
    # FUEL_OIL_NO_5_AND_NO_6 = 7
    # DISTRICT_STEAM = 8
    # DISTRICT_HOT_WATER = 9
    # DISTRICT_CHILLED_WATER = 10
    # PROPANE = 11
    # LIQUID_PROPANE = 12  # This and "PROPANE" are combined
    # KEROSENE = 13
    # DIESEL = 14
    # COAL = 15  # not in list
    # COAL_ANTHRACITE = 16
    # COAL_BITUMINOUS = 17
    # COKE = 18
    # WOOD = 19
    # OTHER = 20
    # WATER = 21  # not in list
    #
    # ENERGY_TYPES = (
    #     (ELECTRICITY, 'Electricity'),
    #     (NATURAL_GAS, 'Natural Gas'),
    #     (FUEL_OIL, 'Fuel Oil'),
    #     (FUEL_OIL_NO_1, 'Fuel Oil No. 1'),
    #     (FUEL_OIL_NO_2, 'Fuel Oil No. 2'),
    #     (FUEL_OIL_NO_4, 'Fuel Oil No. 4'),
    #     (FUEL_OIL_NO_5_AND_NO_6, 'Fuel Oil No. 5 and No. 6'),
    #     (DISTRICT_STEAM, 'District Steam'),
    #     (DISTRICT_HOT_WATER, 'District Hot Water'),
    #     (DISTRICT_CHILLED_WATER, 'District Chilled Water'),
    #     (PROPANE, 'Propane'),
    #     (LIQUID_PROPANE, 'Liquid Propane'),
    #     (KEROSENE, 'Kerosene'),
    #     (DIESEL, 'Diesel'),
    #     (COAL, 'Coal'),
    #     (COAL_ANTHRACITE, 'Coal Anthracite'),
    #     (COAL_BITUMINOUS, 'Coal Bituminous'),
    #     (COKE, 'Coke'),
    #     (WOOD, 'Wood'),
    #     (OTHER, 'Other'),
    # )

    # If validation of unit and type combination is desired
    # from collections import defaultdict
    # valid_energy_units = defaultdict(lambda: [])
    #
    # valid_energy_units['Electricity'].append('kBtu (thousand Btu)')
    # valid_energy_units['Electricity'].append('MBtu (million Btu)')
    # valid_energy_units['Electricity'].append('kWh (thousand Watt-hours)')
    # valid_energy_units['Electricity'].append('MWh (million Watt-hours)')
    # valid_energy_units['Natural Gas'].append('kBtu (thousand Btu)')
    # valid_energy_units['Natural Gas'].append('MBtu (million Btu)')
    # valid_energy_units['Natural Gas'].append('cf (cubic feet)')
    # valid_energy_units['Natural Gas'].append('ccf (hundred cubic feet)')
    # valid_energy_units['Natural Gas'].append('kcf (thousand cubic feet)')
    # valid_energy_units['Natural Gas'].append('MCF(million cubic feet)')
    # valid_energy_units['Natural Gas'].append('therms')
    # valid_energy_units['Natural Gas'].append('cm (Cubic meters)')
    # valid_energy_units['District Steam'].append('kBtu (thousand Btu)')
    # valid_energy_units['District Steam'].append('MBtu (million Btu)')
    # valid_energy_units['District Steam'].append('pounds')
    # valid_energy_units['District Steam'].append('KLbs. (thousand pounds)')
    # valid_energy_units['District Steam'].append('MLbs. (million pounds)')
    # valid_energy_units['District Steam'].append('therms')
    # valid_energy_units['District Hot Water'].append('kBtu (thousand Btu)')
    # valid_energy_units['District Hot Water'].append('MBtu (million Btu)')
    # valid_energy_units['District Hot Water'].append('therms')
    # valid_energy_units['District Chilled Water'].append('kBtu (thousand Btu)')
    # valid_energy_units['District Chilled Water'].append('MBtu (million Btu)')
    # valid_energy_units['District Chilled Water'].append('ton hours')
    # valid_energy_units['Kerosene'].append('kBtu (thousand Btu)')
    # valid_energy_units['Kerosene'].append('MBtu (million Btu)')
    # valid_energy_units['Kerosene'].append('Gallons (US)')
    # valid_energy_units['Kerosene'].append('Liters')
    # valid_energy_units['Fuel Oil (No. 1)'].append('kBtu (thousand Btu)')
    # valid_energy_units['Fuel Oil (No. 1)'].append('MBtu (million Btu)')
    # valid_energy_units['Fuel Oil (No. 1)'].append('Gallons (US)')
    # valid_energy_units['Fuel Oil (No. 1)'].append('Liters')
    # valid_energy_units['Diesel'].append('kBtu (thousand Btu)')
    # valid_energy_units['Diesel'].append('MBtu (million Btu)')
    # valid_energy_units['Diesel'].append('Gallons (US)')
    # valid_energy_units['Diesel'].append('Liters')
    # valid_energy_units['Fuel Oil (No. 2)'].append('kBtu (thousand Btu)')
    # valid_energy_units['Fuel Oil (No. 2)'].append('MBtu (million Btu)')
    # valid_energy_units['Fuel Oil (No. 2)'].append('Gallons (US)')
    # valid_energy_units['Fuel Oil (No. 2)'].append('Liters')
    # valid_energy_units['Propane and Liquid Propane'].append('kBtu (thousand Btu)')
    # valid_energy_units['Propane and Liquid Propane'].append('MBtu (million Btu)')
    # valid_energy_units['Propane and Liquid Propane'].append('cf (cubic feet)')
    # valid_energy_units['Propane and Liquid Propane'].append('kcf (thousand cubic feet)')
    # valid_energy_units['Propane and Liquid Propane'].append('Gallons (US)')
    # valid_energy_units['Propane and Liquid Propane'].append('Liters')
    # valid_energy_units['Fuel Oil (No. 4)'].append('kBtu (thousand Btu)')
    # valid_energy_units['Fuel Oil (No. 4)'].append('MBtu (million Btu)')
    # valid_energy_units['Fuel Oil (No. 4)'].append('Gallons (US)')
    # valid_energy_units['Fuel Oil (No. 4)'].append('Liters')
    # valid_energy_units['Fuel Oil (No. 5 & No. 6)'].append('kBtu (thousand Btu)')
    # valid_energy_units['Fuel Oil (No. 5 & No. 6)'].append('MBtu (million Btu)')
    # valid_energy_units['Fuel Oil (No. 5 & No. 6)'].append('Gallons (US)')
    # valid_energy_units['Fuel Oil (No. 5 & No. 6)'].append('Liters')
    # valid_energy_units['Coal (anthracite)'].append('kBtu (thousand Btu)')
    # valid_energy_units['Coal (anthracite)'].append('MBtu (million Btu)')
    # valid_energy_units['Coal (anthracite)'].append('tons')
    # valid_energy_units['Coal (anthracite)'].append('pounds')
    # valid_energy_units['Coal (anthracite)'].append('KLbs. (thousand pounds)')
    # valid_energy_units['Coal (anthracite)'].append('MLbs. (million pounds)')
    # valid_energy_units['Coal (bituminous)'].append('kBtu (thousand Btu)')
    # valid_energy_units['Coal (bituminous)'].append('MBtu (million Btu)')
    # valid_energy_units['Coal (bituminous)'].append('tons')
    # valid_energy_units['Coal (bituminous)'].append('pounds')
    # valid_energy_units['Coal (bituminous)'].append('KLbs. (thousand pounds)')
    # valid_energy_units['Coal (bituminous)'].append('MLbs')
    # valid_energy_units['Coke'].append('kBtu (thousand Btu)')
    # valid_energy_units['Coke'].append('MBtu (million Btu)')
    # valid_energy_units['Coke'].append('tons')
    # valid_energy_units['Coke'].append('pounds')
    # valid_energy_units['Coke'].append('KLbs. (thousand pounds)')
    # valid_energy_units['Coke'].append('MLbs. (million pounds)')
    # valid_energy_units['Wood'].append('kBtu (thousand Btu)')
    # valid_energy_units['Wood'].append('MBtu (million Btu)')
    # valid_energy_units['Wood'].append('tons')
    # valid_energy_units['Other'].append('kBtu (thousand Btu)')
    # valid_energy_units['Electricity - on site renewable'].append('kBtu (thousand Btu)')
    # valid_energy_units['Electricity - on site renewable'].append('MBtu (million Btu)')
    # valid_energy_units['Electricity - on site renewable'].append('kWh (thousand Watt-hours)')
    # valid_energy_units['Electricity - on site renewable'].append('MWh (million Watt-hours)')

    # Taken from https://portfoliomanager.zendesk.com/hc/en-us/articles/211025388-Is-there-a-list-of-valid-property-level-energy-meter-types-and-unit-of-measure-combinations-
    COAL_ANTHRACITE = 1
    COAL_BITUMINOUS = 2
    COKE = 3
    DIESEL = 4
    DISTRICT_CHILLED_WATER = 5
    DISTRICT_HOT_WATER = 6
    DISTRICT_STEAM = 7
    ELECTRICITY = 8
    ELECTRICITY_ON_SITE_RENEWABLE = 9
    FUEL_OIL_NO_1 = 10
    FUEL_OIL_NO_2 = 11
    FUEL_OIL_NO_4 = 12
    FUEL_OIL_NO_5_AND_NO_6 = 13
    KEROSENE = 14
    NATURAL_GAS = 15
    OTHER = 16
    PROPANE = 17
    WOOD = 18

    ENERGY_TYPES = (
        (COAL_ANTHRACITE, 'Coal (anthracite)'),
        (COAL_BITUMINOUS, 'Coal (bituminous)'),
        (COKE, 'Coke'),
        (DIESEL, 'Diesel'),
        (DISTRICT_CHILLED_WATER, 'District Chilled Water'),
        (DISTRICT_HOT_WATER, 'District Hot Water'),
        (DISTRICT_STEAM, 'District Steam'),
        (ELECTRICITY, 'Electricity'),
        (ELECTRICITY_ON_SITE_RENEWABLE, 'Electricity - on site renewable'),
        (FUEL_OIL_NO_1, 'Fuel Oil (No. 1)'),
        (FUEL_OIL_NO_2, 'Fuel Oil (No. 2)'),
        (FUEL_OIL_NO_4, 'Fuel Oil (No. 4)'),
        (FUEL_OIL_NO_5_AND_NO_6, 'Fuel Oil (No. 5 & No. 6)'),
        (KEROSENE, 'Kerosene'),
        (NATURAL_GAS, 'Natural Gas'),
        (OTHER, 'Other'),
        (PROPANE, 'Propane and Liquid Propane'),
        (WOOD, 'Wood'),
    )

    type_lookup = dict((reversed(type) for type in ENERGY_TYPES))

    PROPERTY_MANAGER = 1
    GREENBUTTON = 2
    BUILDINGSYNC = 3

    SOURCES = (
        (PROPERTY_MANAGER, 'Property Manager'),
        (GREENBUTTON, 'GreenButton'),
        (BUILDINGSYNC, 'BuildingSync'),
    )

    source_lookup = dict((reversed(source) for source in SOURCES))

    property = models.ForeignKey(
        Property,
        related_name='meters',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    source = models.IntegerField(choices=SOURCES)
    source_id = models.CharField(max_length=255, null=True, blank=True)

    type = models.IntegerField(choices=ENERGY_TYPES)
    # units = models.IntegerField(choices=ENERGY_UNITS)


class MeterReading(models.Model):
    meter = models.ForeignKey(
        Meter,
        related_name='meter_readings',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    start_time = models.DateTimeField(db_index=True, primary_key=True)
    end_time = models.DateTimeField(db_index=True)

    reading = QuantityField('kBtu')
    # cost = models.DecimalField(max_digits=11, decimal_places=4, null=True)

    class Meta:
        unique_together = ('meter', 'start_time', 'end_time')


# For migration - delete later once schema is closer to finalized
# from django.contrib.postgres.operations import CreateExtension
# CreateExtension('timescaledb'),
# migrations.RunSQL("ALTER TABLE seed_meterreading DROP CONSTRAINT seed_meterreading_pkey"),
# migrations.RunSQL("SELECT create_hypertable('seed_meterreading', 'start_time');"),
