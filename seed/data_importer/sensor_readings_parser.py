# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from pytz import timezone

from config.settings.common import TIME_ZONE
from seed.lib.mcm import reader
from seed.models import Sensor


class SensorsReadingsParser(object):
    """
    This class parses and validates different details about sensor readings
    Import File - including sensor types & units - to be created before execution.

    The expected input is a csv/xlsx. The columns headers should be:

        - timestamp : datetime (required, unique)

    then any number of column where the header is a Sensor column_name, and the rows are doubles

    It's able to create a collection of Sensor Readings object details.
    """

    _tz = timezone(TIME_ZONE)

    def __init__(self, org_id, sensor_readings_details, data_logger_id):
        # defaulted to None to show it hasn't been cached yet
        self.sensor_readings_details = sensor_readings_details
        self._org_id = org_id
        self._data_logger_id = data_logger_id

    @classmethod
    def factory(cls, sensor_readings_file, org_id, data_logger_id):
        """Factory function for sensorReadingsParser

        :param sensor_readings_file: File
        :param org_id: int
        :param data_logger_id: int, id of data_logger
        :return: SensorReadingsParser
        """
        parser = reader.MCMParser(sensor_readings_file)
        raw_sensor_readings_data = list(parser.data)

        try:
            keys = list(raw_sensor_readings_data[0].keys())
        except IndexError:
            raise ValueError("File has no rows")

        if "timestamp" not in keys:
            raise ValueError("File does not contain correct columns")

        sensor_names = keys
        sensor_names.remove("timestamp")

        sensor_readings_by_sensor_name = {sensor_name: {} for sensor_name in sensor_names}

        for reading in raw_sensor_readings_data:
            timestamp = reading["timestamp"]
            for sensor_name in sensor_names:
                sensor_readings_by_sensor_name[sensor_name][timestamp] = reading[sensor_name]

        return cls(org_id, sensor_readings_by_sensor_name, data_logger_id=data_logger_id)

    def get_validation_report(self):
        sensor_names = Sensor.objects.filter(data_logger=self._data_logger_id).values_list('column_name', flat=True)

        result = [
            {
                "column_name": sensor_name,
                "exists": sensor_name in sensor_names,
                "num_readings": sum((v != "0" and v is not None) for v in readings.values())
            }
            for sensor_name, readings in self.sensor_readings_details.items()
        ]

        return result
