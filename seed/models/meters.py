# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""

from django.db import (
    connection,
    models,
)
from seed.models import Property, Scenario


class Meter(models.Model):
    COAL_ANTHRACITE = 1
    COAL_BITUMINOUS = 2
    COKE = 3
    DIESEL = 4
    DISTRICT_CHILLED_WATER_ABSORPTION = 5
    DISTRICT_CHILLED_WATER_ELECTRIC = 6
    DISTRICT_CHILLED_WATER_ENGINE = 7
    DISTRICT_CHILLED_WATER_OTHER = 8
    DISTRICT_HOT_WATER = 9
    DISTRICT_STEAM = 10
    ELECTRICITY_GRID = 11
    ELECTRICITY_SOLAR = 12
    ELECTRICITY_WIND = 13
    FUEL_OIL_NO_1 = 14
    FUEL_OIL_NO_2 = 15
    FUEL_OIL_NO_4 = 16
    FUEL_OIL_NO_5_AND_NO_6 = 13
    KEROSENE = 18
    NATURAL_GAS = 19
    OTHER = 20
    PROPANE = 21
    WOOD = 22
    COST = 23

    # Taken from EnergyStar Portfolio Manager
    ENERGY_TYPES = (
        (COAL_ANTHRACITE, 'Coal (anthracite)'),
        (COAL_BITUMINOUS, 'Coal (bituminous)'),
        (COKE, 'Coke'),
        (DIESEL, 'Diesel'),
        (DISTRICT_CHILLED_WATER_ABSORPTION, 'District Chilled Water - Absorption'),
        (DISTRICT_CHILLED_WATER_ELECTRIC, 'District Chilled Water - Electric'),
        (DISTRICT_CHILLED_WATER_ENGINE, 'District Chilled Water - Engine'),
        (DISTRICT_CHILLED_WATER_OTHER, 'District Chilled Water - Other'),
        (DISTRICT_HOT_WATER, 'District Hot Water'),
        (DISTRICT_STEAM, 'District Steam'),
        (ELECTRICITY_GRID, 'Electric - Grid'),
        (ELECTRICITY_SOLAR, 'Electric - Solar'),
        (ELECTRICITY_WIND, 'Electric - Wind'),
        (FUEL_OIL_NO_1, 'Fuel Oil (No. 1)'),
        (FUEL_OIL_NO_2, 'Fuel Oil (No. 2)'),
        (FUEL_OIL_NO_4, 'Fuel Oil (No. 4)'),
        (FUEL_OIL_NO_5_AND_NO_6, 'Fuel Oil (No. 5 and No. 6)'),
        (KEROSENE, 'Kerosene'),
        (NATURAL_GAS, 'Natural Gas'),
        (OTHER, 'Other:'),
        (PROPANE, 'Propane'),
        (WOOD, 'Wood'),
        (COST, 'Cost'),
    )

    type_lookup = dict((reversed(type) for type in ENERGY_TYPES))

    PORTFOLIO_MANAGER = 1
    GREENBUTTON = 2
    BUILDINGSYNC = 3

    SOURCES = (
        (PORTFOLIO_MANAGER, 'Portfolio Manager'),
        (GREENBUTTON, 'GreenButton'),
        (BUILDINGSYNC, 'BuildingSync'),
    )

    is_virtual = models.BooleanField(default=False)

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='meters',
        null=True,
        blank=True
    )

    source = models.IntegerField(choices=SOURCES, default=None, null=True)
    source_id = models.CharField(max_length=255, null=True, blank=True)

    type = models.IntegerField(choices=ENERGY_TYPES, default=None, null=True)

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    def copy_readings(self, source_meter, overlaps_possible=True):
        """
        Copies MeterReadings of another Meter. By default, overlapping readings
        are considered possible so a SQL bulk upsert is used. But if overlapping
        readings are explicitly specified as not possible, a more efficient
        bulk_create is used.
        """
        if overlaps_possible:
            reading_strings = [
                f"({self.id}, '{reading.start_time}', '{reading.end_time}', {reading.reading}, '{reading.source_unit}', {reading.conversion_factor})"
                for reading
                in source_meter.meter_readings.all()
            ]

            sql = (
                "INSERT INTO seed_meterreading(meter_id, start_time, end_time, reading, source_unit, conversion_factor)" +
                " VALUES " + ", ".join(reading_strings) +
                " ON CONFLICT (meter_id, start_time, end_time)" +
                " DO UPDATE SET reading = EXCLUDED.reading, source_unit = EXCLUDED.source_unit, conversion_factor = EXCLUDED.conversion_factor" +
                " RETURNING reading;"
            )

            with connection.cursor() as cursor:
                cursor.execute(sql)
        else:
            readings = {
                MeterReading(
                    start_time=reading.start_time,
                    end_time=reading.end_time,
                    reading=reading.reading,
                    source_unit=reading.source_unit,
                    conversion_factor=reading.conversion_factor,
                    meter_id=self.id,
                )
                for reading
                in source_meter.meter_readings.all()
            }

            MeterReading.objects.bulk_create(readings)


class MeterReading(models.Model):
    meter = models.ForeignKey(
        Meter,
        on_delete=models.CASCADE,
        related_name='meter_readings',
        null=True,
        blank=True
    )

    start_time = models.DateTimeField(db_index=True, primary_key=True)
    end_time = models.DateTimeField(db_index=True)

    reading = models.FloatField(null=True)

    # The following two fields are tracked for historical purposes
    source_unit = models.CharField(max_length=255, null=True, blank=True)
    conversion_factor = models.FloatField()

    class Meta:
        unique_together = ('meter', 'start_time', 'end_time')
