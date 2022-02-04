# !/usr/bin/env python
# encoding: utf-8

from config.settings.common import TIME_ZONE

from pytz import timezone

from seed.lib.mcm import reader


class SensorsParser(object):
    """
    This class parses and validates different details about a sensor
    Import File - including sensor types & units - to be created before execution.

    The expected input is a csv/xlsx. The columns headers should be:

        - display_name : str (required, unique)
        - type : str (required)
        - location_identifier:  str
        - units: str (required)
        - column_name: str (required, unique)
        - description: str

    It's able to create a collection of Sensors object details.
    """

    _tz = timezone(TIME_ZONE)

    def __init__(self, org_id, sensor_details, property_id=None):
        # defaulted to None to show it hasn't been cached yet
        self._cache_meter_objs = None
        self._cache_org_country = None

        self.sensor_details = sensor_details
        self._org_id = org_id
        self._property_id = property_id
        self._unique_meters = {}

        self._source_to_property_ids = {}  # tracked to reduce the number of database queries

        # The following are only relevant/used if property_id isn't explicitly specified
        if property_id is None:
            self._property_link = 'Portfolio Manager ID'
            self._unlinkable_pm_ids = set()  # to avoid duplicates

    @classmethod
    def factory(cls, sensors_file, org_id, property_id=None):
        """Factory function for sensorsParser

        :param sensors_file: File
        :param org_id: int
        :param property_id: int, id of property - required if sensor data is for a specific property
        :return: SensorsParser
        """
        parser = reader.MCMParser(sensors_file)
        raw_sensor_data = list(parser.data)
        return cls(org_id, raw_sensor_data, property_id=property_id)

    def get_validated_sensors(self):
        """
        Creates/returns the validated type and unit combinations given in the
        import file.

        This is done by building a set of tuples containing type and unit
        combinations found in the parsed meter details. Since a set is used,
        these are deduplicated.
        """
        return self.sensor_details
