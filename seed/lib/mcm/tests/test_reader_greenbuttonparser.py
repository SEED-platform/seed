# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import os

from django.test import TestCase

from seed.lib.mcm.reader import GreenButtonParser


class GreenButtonParserTest(TestCase):
    def test_data_property_can_handle_electricity_wh(self):
        # Case when powerOfTenMultiplier + base unit = exact match of known unit
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-electricity-wh.xml"
        with open(filepath, "r", encoding="utf-8") as f:
            parser = GreenButtonParser(f)
            results = parser.data

        expectation = [
            {
                'start_time': 1299387600,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Electric - Grid',
                'Usage Units': 'Wh (Watt-hours)',
                'Usage/Quantity': 1790.0,
            },
            {
                'start_time': 1299388500,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Electric - Grid',
                'Usage Units': 'Wh (Watt-hours)',
                'Usage/Quantity': 1792.0,
            }
        ]
        self.assertEqual(results, expectation)

    def test_data_property_can_handle_gas_MBtu(self):
        # Different case when powerOfTenMultiplier + base unit = exact match of known unit
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-gas-MBtu.xml"
        with open(filepath, "r", encoding="utf-8") as f:
            parser = GreenButtonParser(f)
            results = parser.data

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

        self.assertEqual(results, expectation)

    def test_data_property_can_handle_gas_J_with_power_of_ten_of_negative_3(self):
        # Case when base unit approximated and powerOfTenMultiplier used as conversion
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-gas-J--3.xml"
        with open(filepath, "r", encoding="utf-8") as f:
            parser = GreenButtonParser(f)
            results = parser.data

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

        self.assertEqual(results, expectation)

    def test_data_property_can_handle_gas_therms_with_power_of_ten_of_negative_3(self):
        # Case when only base unit == exact match and powerOfTenMultiplier used as conversion
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-gas-therms--3.xml"
        with open(filepath, "r", encoding="utf-8") as f:
            parser = GreenButtonParser(f)
            results = parser.data

        expectation = [
            {
                'start_time': 1299387600,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Natural Gas',
                'Usage Units': 'therms',
                'Usage/Quantity': 1790.0 / 10**3,
            },
            {
                'start_time': 1299388500,
                'source_id': 'User/6150855/UsagePoint/409483/MeterReading/1/IntervalBlock/1',
                'duration': 900,
                'Meter Type': 'Natural Gas',
                'Usage Units': 'therms',
                'Usage/Quantity': 1792.0 / 10**3,
            }
        ]

        self.assertEqual(results, expectation)

    def test_data_property_can_handle_invalid_energy_type_of_time(self):
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-invalid-time-service-kind.xml"
        with open(filepath, "r", encoding="utf-8") as f:
            parser = GreenButtonParser(f)
            results = parser.data

        self.assertEqual(results, [])

    def test_data_property_can_handle_invalid_electricity_cubic_feet(self):
        filepath = os.path.dirname(os.path.abspath(__file__)) + "/test_data/greenbutton/example-GreenButton-data-invalid-electricity-cf.xml"
        with open(filepath, "r", encoding="utf-8") as f:
            parser = GreenButtonParser(f)
            results = parser.data

        self.assertEqual(results, [])
