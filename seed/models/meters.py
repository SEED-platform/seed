"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import IntegrityError, connection, models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from psycopg2.extras import execute_values

from seed.models import Property, Scenario
from seed.models.inventory_groups import InventoryGroupMapping


class Meter(models.Model):
    ## CONNECTION TYPES
    # These connection types do not require services. May be on a property or system
    IMPORTED = 1  # tracks what is received via an unknown source
    EXPORTED = 2  # tracks what is expelled via an unknown source

    # These connection types require services. May be on a property or system
    RECEIVING_SERVICE = 3  # tracks what is received via my service
    RETURNING_TO_SERVICE = 4  # tracks what is expelled via my service

    # These connection types require services and may only be on Systems
    TOTAL_FROM_USERS = 5  # tracks everything that this system expelled via my service
    TOTAL_TO_USERS = 6  # tracks everything that this system received via my service

    CONNECTION_TYPES = (
        (IMPORTED, "Imported"),
        (EXPORTED, "Exported"),
        (RECEIVING_SERVICE, "Receiving Service"),
        (RETURNING_TO_SERVICE, "Returning To Service"),
        (TOTAL_FROM_USERS, "Total From Users"),
        (TOTAL_TO_USERS, "Total To Users"),
    )

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
    FUEL_OIL_NO_5_AND_NO_6 = 17
    KEROSENE = 18
    NATURAL_GAS = 19
    OTHER = 20
    PROPANE = 21
    WOOD = 22
    COST = 23
    ELECTRICITY_UNKNOWN = 24
    POTABLE_INDOOR = 27
    POTABLE_MIXED = 28
    POTABLE_OUTDOOR = 29
    HEATING_DEGREE_DAYS = 30
    COOLING_DEGREE_DAYS = 31
    AVERAGE_TEMPERATURE = 32
    CUSTOM_METER = 99

    # Taken from EnergyStar Portfolio Manager
    ENERGY_TYPES = (
        (COAL_ANTHRACITE, "Coal (anthracite)"),
        (COAL_BITUMINOUS, "Coal (bituminous)"),
        (COKE, "Coke"),
        (DIESEL, "Diesel"),
        (DISTRICT_CHILLED_WATER, "District Chilled Water"),
        (DISTRICT_CHILLED_WATER_ABSORPTION, "District Chilled Water - Absorption"),
        (DISTRICT_CHILLED_WATER_ELECTRIC, "District Chilled Water - Electric"),
        (DISTRICT_CHILLED_WATER_ENGINE, "District Chilled Water - Engine"),
        (DISTRICT_CHILLED_WATER_OTHER, "District Chilled Water - Other"),
        (DISTRICT_HOT_WATER, "District Hot Water"),
        (DISTRICT_STEAM, "District Steam"),
        (ELECTRICITY, "Electric"),
        (ELECTRICITY_GRID, "Electric - Grid"),
        (ELECTRICITY_SOLAR, "Electric - Solar"),
        (ELECTRICITY_WIND, "Electric - Wind"),
        (FUEL_OIL_NO_1, "Fuel Oil (No. 1)"),
        (FUEL_OIL_NO_2, "Fuel Oil (No. 2)"),
        (FUEL_OIL_NO_4, "Fuel Oil (No. 4)"),
        (FUEL_OIL_NO_5_AND_NO_6, "Fuel Oil (No. 5 and No. 6)"),
        (KEROSENE, "Kerosene"),
        (NATURAL_GAS, "Natural Gas"),
        (OTHER, "Other:"),
        (PROPANE, "Propane"),
        (WOOD, "Wood"),
        (COST, "Cost"),
        (ELECTRICITY_UNKNOWN, "Electric - Unknown"),
        (CUSTOM_METER, "Custom Meter"),
        (POTABLE_INDOOR, "Potable Indoor"),
        (POTABLE_OUTDOOR, "Potable Outdoor"),
        (POTABLE_MIXED, "Potable: Mixed Indoor/Outdoor"),
        (HEATING_DEGREE_DAYS, "Heating Degree Days"),
        (COOLING_DEGREE_DAYS, "Cooling Degree Days"),
        (AVERAGE_TEMPERATURE, "Average Temperature"),
    )
    ENERGY_TYPE_BY_METER_TYPE = dict(ENERGY_TYPES)

    # list of header strings and their related energy types. These are used
    # when parsing ESPM files to map the columns headers to the correct meter
    # types.
    ENERGY_TYPE_BY_HEADER_STRING = {
        # these mappings are assumed based on ESPM values [old format]
        "Coal Use (Anthracite)": ENERGY_TYPE_BY_METER_TYPE[COAL_ANTHRACITE],
        "Coal Use (Bituminous)": ENERGY_TYPE_BY_METER_TYPE[COAL_BITUMINOUS],
        "Coke": ENERGY_TYPE_BY_METER_TYPE[COKE],
        "Diesel": ENERGY_TYPE_BY_METER_TYPE[DIESEL],
        "District Chilled Water Use (Absorption)": ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_ABSORPTION],
        "District Chilled Water Use (Electric)": ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_ELECTRIC],
        "District Chilled Water Use (Engine)": ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_ENGINE],
        "District Chilled Water Use (Other)": ENERGY_TYPE_BY_METER_TYPE[DISTRICT_CHILLED_WATER_OTHER],
        "District Hot Water Use": ENERGY_TYPE_BY_METER_TYPE[DISTRICT_HOT_WATER],
        "District Steam Use": ENERGY_TYPE_BY_METER_TYPE[DISTRICT_STEAM],
        "Electricity Use (Grid)": ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_GRID],
        "Electricity Use (Solar)": ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_SOLAR],
        "Electricity Use (Wind)": ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_WIND],
        "Fuel Oil Use (No. 1)": ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_1],
        "Fuel Oil Use (No. 2)": ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_2],
        "Fuel Oil Use (No. 4)": ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_4],
        "Fuel Oil Use (No. 5 and No. 6)": ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_5_AND_NO_6],
        "Kerosene Use": ENERGY_TYPE_BY_METER_TYPE[KEROSENE],
        "Natural Gas Use": ENERGY_TYPE_BY_METER_TYPE[NATURAL_GAS],
        "Other Use": ENERGY_TYPE_BY_METER_TYPE[OTHER],
        "Propane Use": ENERGY_TYPE_BY_METER_TYPE[PROPANE],
        "Wood Use": ENERGY_TYPE_BY_METER_TYPE[WOOD],
        "Electricity Use (Unknown)": ENERGY_TYPE_BY_METER_TYPE[ELECTRICITY_UNKNOWN],
        # these values are added based on known usage
        "Fuel Oil #2 Use": ENERGY_TYPE_BY_METER_TYPE[FUEL_OIL_NO_2],
        "Diesel #2 Use": ENERGY_TYPE_BY_METER_TYPE[DIESEL],
    }

    type_lookup = {name: id for id, name in ENERGY_TYPES}

    PORTFOLIO_MANAGER = 1
    GREENBUTTON = 2
    BUILDINGSYNC = 3
    PORTFOLIO_MANAGER_DATA_REQUEST = 4
    MANUAL_ENTRY = 5

    SOURCES = (
        (PORTFOLIO_MANAGER, "Portfolio Manager"),
        (GREENBUTTON, "GreenButton"),
        (BUILDINGSYNC, "BuildingSync"),
        (PORTFOLIO_MANAGER_DATA_REQUEST, "Portfolio Manager"),
        (MANUAL_ENTRY, "Manual Entry"),
    )

    # The alias can be thought of as the "name" of the meter. Not
    # sure why we don't have a name field.
    alias = models.CharField(max_length=255, null=True, blank=True)
    is_virtual = models.BooleanField(default=False)

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="meters", null=True, blank=True)
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, null=True, blank=True)
    system = models.ForeignKey("System", on_delete=models.CASCADE, related_name="meters", null=True, blank=True)

    source = models.IntegerField(choices=SOURCES, default=None, null=True)
    source_id = models.CharField(max_length=255, null=True, blank=True)

    type = models.IntegerField(choices=ENERGY_TYPES, default=None, null=True)

    service = models.ForeignKey("Service", on_delete=models.SET_NULL, related_name="meters", null=True, blank=True)
    connection_type = models.IntegerField(choices=CONNECTION_TYPES, default=IMPORTED, null=False)

    def copy_readings(self, source_meter, overlaps_possible=True):
        """
        Copies MeterReadings of another Meter. By default, overlapping readings
        are considered possible so a SQL bulk upsert is used. But if overlapping
        readings are explicitly specified as not possible, a more efficient
        bulk_create is used.
        """
        if overlaps_possible:
            sql = (
                "INSERT INTO seed_meterreading(meter_id, start_time, end_time, reading, source_unit, conversion_factor) "
                "VALUES %s "
                "ON CONFLICT (meter_id, start_time, end_time) "
                "DO UPDATE SET reading=excluded.reading, source_unit=excluded.source_unit, conversion_factor=excluded.conversion_factor "
                "RETURNING reading"
            )

            with connection.cursor() as cursor:
                execute_values(
                    cursor,
                    sql,
                    source_meter.meter_readings.values(),
                    template=f"({self.id}, %(start_time)s, %(end_time)s, %(reading)s, %(source_unit)s, %(conversion_factor)s)",
                )
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


@receiver(pre_save, sender=Meter)
def presave_meter(sender, instance, **kwargs):
    property = instance.property
    system = instance.system
    connection_type = instance.connection_type
    service = instance.service
    connection_string = dict(Meter.CONNECTION_TYPES).get(connection_type)

    # must be connected to either a system or a property
    if property is not None and system is not None:
        raise IntegrityError(f"Meter {instance.id} has both a property and a system. It must only have one.")

    outside_connection = connection_type in [Meter.IMPORTED, Meter.EXPORTED]
    if outside_connection:
        # outside connections don't have services
        if instance.service is not None:
            raise IntegrityError(f"Meter {instance.id} has connection_type '{connection_string}', but also is connected to a service")
    else:
        # inside connections _do_ have services
        if service is None:
            raise IntegrityError(f"Meter {instance.id} has connection_type '{connection_string}', but is not connected to a service")

        total_connections = connection_type in [Meter.TOTAL_FROM_USERS, Meter.TOTAL_TO_USERS]
        if total_connections:
            # Only systems have connection type "total"
            if system is None:
                raise IntegrityError(f"Meter {instance.id} has connection_type '{connection_string}', but is not connected to a system")

            # Total connections must have a service owned by system
            if system.id != service.system_id:
                raise IntegrityError(
                    f"Meters with connection_type '{connection_string}' must have a service on the system the meter is connected to"
                    # f"Meter {instance.id} on system {system.name} has connection_type '{connection_string}', but is also connected to service {service.name}, which is on a different system, {service.system.name}. Meters with connection_type '{connection_string}' must have a service on the system the meter is connected to"
                )

            # Service should only have one meter of each "total" connection type
            if Meter.objects.filter(service=service, connection_type=connection_type).exclude(pk=instance.pk).exists():
                raise IntegrityError(f"Service {service.id} already has a meter with connection type '{connection_string}'")

        elif property:  # Meter.RETURNING_TO_SERVICE and Meter.RECEIVING_SERVICE
            # service must be within the meter's property's group
            property_groups = InventoryGroupMapping.objects.filter(property=property).values_list("group_id", flat=True)
            if service is not None and service.system.group.id not in property_groups:
                raise IntegrityError(
                    f"Meter {instance.id} on property {property.id} and has service {service.name}, but meter and property are not in the service's group"
                )


class MeterReading(models.Model):
    """
    A meter reading represents the actual usage entry for a given meter.

    NOTE: SEED stores all energy readings in kBtu.  The raw usage reading is converted
    on import to kBtu using the conversion_factor which is determined by the meter type and raw units on import,
    therefore, the reading field of this model will always be in kBtu.

    The original units however when being displayed to the user (e.g., on the Property Detail Meters tab)
    will contain the original units and meter readings.
    """

    meter = models.ForeignKey(Meter, on_delete=models.CASCADE, related_name="meter_readings", null=True, blank=True)

    start_time = models.DateTimeField(db_index=True, primary_key=True)
    end_time = models.DateTimeField(db_index=True)

    reading = models.FloatField(null=True)

    # This field is determined by the raw units of the meter entry upon import
    source_unit = models.CharField(max_length=255, null=True, blank=True)

    # This field is determined by the meter type and raw units upon import
    conversion_factor = models.FloatField()

    class Meta:
        unique_together = ("meter", "start_time", "end_time")
