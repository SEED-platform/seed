# !/usr/bin/env python
# encoding: utf-8

import os

from django.test import TestCase

from seed.lib.mcm.reader import GreenButtonParser


class GreenButtonParserTest(TestCase):
    def test_data_property_can_handle_electricity_wh(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-electricity-wh.xml"
        file = open(file_path, "r", encoding="utf-8")
        parser = GreenButtonParser(file)

        expectation = [
            {
                'start_time': 1299387600,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Electric - Grid',
                'Usage Units': 'kWh (thousand Watt-hours)',
                'Usage/Quantity': 1.79,
            },
            {
                'start_time': 1299388500,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Electric - Grid',
                'Usage Units': 'kWh (thousand Watt-hours)',
                'Usage/Quantity': 1.792,
            }
        ]

        self.assertEqual(parser.data, expectation)

    def test_data_property_can_handle_gas_MBtu(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-gas-MBtu.xml"
        file = open(file_path, "r", encoding="utf-8")
        parser = GreenButtonParser(file)

        expectation = [
            {
                'start_time': 1299387600,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Natural Gas',
                'Usage Units': 'MBtu/MMBtu (million Btu)',
                'Usage/Quantity': 1790.0,  # No conversion/multiplier
            },
            {
                'start_time': 1299388500,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Natural Gas',
                'Usage Units': 'MBtu/MMBtu (million Btu)',
                'Usage/Quantity': 1792.0,  # No conversion/multiplier
            }
        ]

        self.assertEqual(parser.data, expectation)

    def test_data_property_can_handle_gas_J_with_power_of_ten_of_negative_3(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-gas-J--3.xml"
        file = open(file_path, "r", encoding="utf-8")
        parser = GreenButtonParser(file)

        expectation = [
            {
                'start_time': 1299387600,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Natural Gas',
                'Usage Units': 'GJ',
                'Usage/Quantity': 1790.0 / 10**12,
            },
            {
                'start_time': 1299388500,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Natural Gas',
                'Usage Units': 'GJ',
                'Usage/Quantity': 1792.0 / 10**12,
            }
        ]

        self.assertEqual(parser.data, expectation)

    def test_data_property_can_handle_invalid_energy_type_of_time(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-invalid-time-service-kind.xml"
        file = open(file_path, "r", encoding="utf-8")
        parser = GreenButtonParser(file)

        self.assertEqual(parser.data, [])

    def test_data_property_can_handle_invalid_electricity_cubic_feet(self):
        file_path = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-invalid-electricity-cf.xml"
        file = open(file_path, "r", encoding="utf-8")
        parser = GreenButtonParser(file)

        self.assertEqual(parser.data, [])
