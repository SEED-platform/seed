# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import connection, models

from seed.models import Property, Scenario


class Meter(models.Model):
    COAL_ANTHRACITE = 1
    COAL_BITUMINOUS = 2
    COKE = 3
    DIESEL = 4
    DISTRICT_CHILLED_WATER = 25  # renumber this some day?
    DISTRICT_CHILLED_WATER_ABSORPTION = 5
    DISTRICT_CHILLED_WATER_ELECTRIC = 6
    DISTRICT_CHILLED_WATER_ENGINE = 7
    DISTRICT_CHILLED_WATER_OTHER = 8
    DISTRICT_HOT_WATER = 9
    DISTRICT_STEAM = 10
    ELECTRICITY = 26  # renumber this some day?
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
    ELECTRICITY_UNKNOWN = 24
    CUSTOM_METER = 99

    # Taken from EnergyStar Portfolio Manager
    ENERGY_TYPES = (
        (COAL_ANTHRACITE, 'Coal (anthracite)'),
        (COAL_BITUMINOUS, 'Coal (bituminous)'),
        (COKE, 'Coke'),
        (DIESEL, 'Diesel'),
        (DISTRICT_CHILLED_WATER, 'District Chilled Water'),
        (DISTRICT_CHILLED_WATER_ABSORPTION, 'District Chilled Water - Absorption'),
        (DISTRICT_CHILLED_WATER_ELECTRIC, 'District Chilled Water - Electric'),
        (DISTRICT_CHILLED_WATER_ENGINE, 'District Chilled Water - Engine'),
        (DISTRICT_CHILLED_WATER_OTHER, 'District Chilled Water - Other'),
        (DISTRICT_HOT_WATER, 'District Hot Water'),
        (DISTRICT_STEAM, 'District Steam'),
        (ELECTRICITY, 'Electric'),
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
        (ELECTRICITY_UNKNOWN, 'Electric - Unknown'),
        (CUSTOM_METER, 'Custom Meter')
    )
    ENERGY_TYPE_BY_METER_TYPE = dict(ENERGY_TYPES)

    # list of header strings and their related energy types. These are used
    # when parsing ESPM files to map the columns headers to the correct meter
    # types.
    ENERGY_TYPE_BY_HEADER_STRING = {

        # these mappings are assumed based on ESPM values [old format]
        'Coal Use (Anthracite)': ENERGY_TYPE_BY_METER_TYPE[COAL_ANTHRACITE],
        'Coal Use (Bituminous)': ENERGY_TYPE_BY_METER_TYPE[COAL_BITUMINOUS],
        'Coke': ENERGY_TYPE_BY_METER_TYPE[COKE],
        'Diesel': ENERGY_TYPE_BY_METER_TYPE[DIESEL],
        'District Chilled Water Use (Absorption)': ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_ABSORPTION],
        'District Chilled Water Use (Electric)': ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_ELECTRIC],
        'District Chilled Water Use (Engine)': ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_ENGINE],
        'District Chilled Water Use (Other)': ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_OTHER],
        'District Hot Water Use': ENERGY_TYPE_BY_METER_TYPE[DISTRICT_HOT_WATER],
        'District Steam Use': ENERGY_TYPE_BY_METER_TYPE[DISTRICT_STEAM],
        'Electricity Use (Grid)': ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_GRID],
        'Electricity Use (Solar)': ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_SOLAR],
        'Electricity Use (Wind)': ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_WIND],
        'Fuel Oil Use (No. 1)': ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_1],
        'Fuel Oil Use (No. 2)': ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_2],
        'Fuel Oil Use (No. 4)': ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_4],
        'Fuel Oil Use (No. 5 and No. 6)': ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_5_AND_NO_6],
        'Kerosene Use': ENERGY_TYPE_BY_METER_TYPE[KEROSENE],
        'Natural Gas Use': ENERGY_TYPE_BY_METER_TYPE[NATURAL_GAS],
        'Other Use': ENERGY_TYPE_BY_METER_TYPE[OTHER],
        'Propane Use': ENERGY_TYPE_BY_METER_TYPE[PROPANE],
        'Wood Use': ENERGY_TYPE_BY_METER_TYPE[WOOD],
        'Electricity Use (Unknown)': ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_UNKNOWN],

        # these values are added based on known usage
        'Fuel Oil #2 Use': ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_2],
        'Diesel #2 Use': ENERGY_TYPE_BY_METER_TYPE[DIESEL],

    }

    type_lookup = dict((reversed(type) for type in ENERGY_TYPES))  # type: ignore

    PORTFOLIO_MANAGER = 1
    GREENBUTTON = 2
    BUILDINGSYNC = 3
    PORTFOLIO_MANAGER_DATA_REQUEST = 4
    MANUAL_ENTRY = 5

    SOURCES = (
        (PORTFOLIO_MANAGER, 'Portfolio Manager'),
        (GREENBUTTON, 'GreenButton'),
        (BUILDINGSYNC, 'BuildingSync'),
        (PORTFOLIO_MANAGER_DATA_REQUEST, 'Portfolio Manager'),
        (MANUAL_ENTRY, 'Manual Entry'),
    )

    # The alias can be thought of as the "name" of the meter. Not
    # sure why we don't have a name field.
    alias = models.CharField(max_length=255, null=True, blank=True)
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
                for reading in source_meter.meter_readings.all()
            }

            MeterReading.objects.bulk_create(readings)


class MeterReading(models.Model):
    """
    A meter reading represents the actual usage entry for a given meter.

    NOTE: SEED stores all energy readings in kBtu.  The raw usage reading is converted
    on import to kBtu using the conversion_factor which is determined by the meter type and raw units on import,
    therefore, the reading field of this model will always be in kBtu.

    The original units however when being displayed to the user (e.g., on the Property Detail Meters tab)
    will contain the original units and meter readings.
    """
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

    # This field is determined by the raw units of the meter entry upon import
    source_unit = models.CharField(max_length=255, null=True, blank=True)

    # This field is determined by the meter type and raw units upon import
    conversion_factor = models.FloatField()

    class Meta:
        unique_together = ('meter', 'start_time', 'end_time')
