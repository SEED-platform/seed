# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Dan Gunter <dkgunter@lbl.gov>'

Unit tests for map.py
"""

import logging

from django.test import TestCase

from seed.lib.mappings import mapping_columns
from seed.lib.mappings import mapping_data
import json

_log = logging.getLogger(__name__)


class TestMappingColumns(TestCase):
    """Test mapping data methods."""

    def setUp(self):
        self.maxDiff = None
        # emulate columns from covered building sample
        self.raw_columns = [
            'UBI',
            'UBI_BBL',
            'GBA',
            'BLDGS',
            'Address',
            'Owner',
            'City',
            'State',
            'Zip',
            'Property Type',
            'AYB_YearBuilt',
            'extra_data_1',
            'extra_data_2',
        ]

        self.example_mappings = [
            ('PropertyState', 'building_count', 100),
            ('PropertyState', 'gross_floor_area', 75),
            ('PropertyState', 'year_built', 60),
        ]

        self.expected = {
            'City': ['PropertyState', 'city', 100],
            'Zip': ['PropertyState', 'postal_code', 100],
            'GBA': ['PropertyState', 'gross_floor_area', 100],
            'BLDGS': ['PropertyState', 'building_count', 69],
            'AYB_YearBuilt': ['PropertyState', 'year_built', 82],
            'State': ['PropertyState', 'state', 100],
            'Address': ['PropertyState', 'address_line_1', 90],
            'Owner': ['PropertyState', 'owner', 100],
            'extra_data_1': ['PropertyState', 'generation_date', 69],
            'extra_data_2': ['PropertyState', 'release_date', 67],
            'Property Type': ['PropertyState', 'property_notes', 92],
            'UBI': ['PropertyState', 'building_certification', 60],
        }

        self.md = mapping_data.MappingData()

    def test_mapping_columns(self):
        mc = mapping_columns.MappingColumns(self.raw_columns, self.md.keys_with_table_names)

        _log.debug(json.dumps(mc.final_mappings, indent=4))
        self.assertDictEqual(mc.final_mappings, self.expected)

    def test_mapping_columns_with_threshold(self):
        expected = {
            'City': ['PropertyState', 'city', 100],
            'Zip': ['PropertyState', 'postal_code', 100],
            'GBA': ['PropertyState', 'gross_floor_area', 100],
            'BLDGS': ['PropertyState', 'building_count', 69],
            'AYB_YearBuilt': ['PropertyState', 'year_built', 82],
            'State': ['PropertyState', 'state', 100],
            'Address': ['PropertyState', 'address_line_1', 90],
            'Owner': ['PropertyState', 'owner', 100],
            'extra_data_1': ['PropertyState', 'generation_date', 69],
            'extra_data_2': ['PropertyState', 'extra_data_2', 100],
            'Property Type': ['PropertyState', 'property_notes', 92],
            'UBI': ['PropertyState', 'UBI', 100],
            'UBI_BBL': ['PropertyState', 'UBI_BBL', 100],
        }

        mc = mapping_columns.MappingColumns(self.raw_columns,
                                            self.md.keys_with_table_names,
                                            threshold=69)
        self.assertDictEqual(mc.final_mappings, expected)

        expected = {
            'City': ['PropertyState', 'city', 100],
            'Zip': ['PropertyState', 'postal_code', 100],
            'GBA': ['PropertyState', 'gross_floor_area', 100],
            'BLDGS': ['PropertyState', 'BLDGS', 100],
            'AYB_YearBuilt': ['PropertyState', 'year_built', 82],
            'State': ['PropertyState', 'state', 100],
            'Address': ['PropertyState', 'address_line_1', 90],
            'Owner': ['PropertyState', 'owner', 100],
            'extra_data_1': ['PropertyState', 'extra_data_1', 100],
            'extra_data_2': ['PropertyState', 'extra_data_2', 100],
            'Property Type': ['PropertyState', 'property_notes', 92],
            'UBI': ['PropertyState', 'UBI', 100],
            'UBI_BBL': ['PropertyState', 'UBI_BBL', 100],
        }
        mc = mapping_columns.MappingColumns(self.raw_columns,
                                            self.md.keys_with_table_names,
                                            threshold=80)
        self.assertDictEqual(mc.final_mappings, expected)

        expected = {
            'City': ['PropertyState', 'city', 100],
            'Zip': ['PropertyState', 'postal_code', 100],
            'GBA': ['PropertyState', 'gross_floor_area', 100],
            'BLDGS': ['PropertyState', 'BLDGS', 100],
            'AYB_YearBuilt': ['PropertyState', 'AYB_YearBuilt', 100],
            'State': ['PropertyState', 'state', 100],
            'Address': ['PropertyState', 'Address', 100],
            'Owner': ['PropertyState', 'owner', 100],
            'extra_data_1': ['PropertyState', 'extra_data_1', 100],
            'extra_data_2': ['PropertyState', 'extra_data_2', 100],
            'Property Type': ['PropertyState', 'Property Type', 100],
            'UBI': ['PropertyState', 'UBI', 100],
            'UBI_BBL': ['PropertyState', 'UBI_BBL', 100],
        }
        mc = mapping_columns.MappingColumns(self.raw_columns,
                                            self.md.keys_with_table_names,
                                            threshold=100)
        self.assertDictEqual(mc.final_mappings, expected)

    def test_add_mappings(self):
        mc = mapping_columns.MappingColumns(
            self.raw_columns,
            self.md.keys_with_table_names
        )

        result = mc.add_mappings('new', [('a', 'b', 100)])
        self.assertTrue(result)

        result = mc.add_mappings('new', [('a', 'b', 100)])
        self.assertFalse(result)

    def test_first_suggested_mapping(self):
        mc = mapping_columns.MappingColumns(
            self.raw_columns,
            self.md.keys_with_table_names
        )

        expected = ('PropertyState', 'city', 100)
        result = mc.first_suggested_mapping('City')
        self.assertTupleEqual(result, expected)

        with self.assertRaises(KeyError):
            mc.first_suggested_mapping('bad-key')

    def test_sort_duplicates(self):
        data = [
            {'raw_column': 'Building Count', 'confidence': 69},
            {'raw_column': 'EUI', 'confidence': 62},
            {'raw_column': 'Zenith', 'confidence': 90},
            {'raw_column': 'Altitude', 'confidence': 90},
            {'raw_column': 'Annual EUI', 'confidence': 62},
        ]

        expected = [
            {'raw_column': 'Altitude', 'confidence': 90},
            {'raw_column': 'Zenith', 'confidence': 90},
            {'raw_column': 'Building Count', 'confidence': 69},
            {'raw_column': 'Annual EUI', 'confidence': 62},
            {'raw_column': 'EUI', 'confidence': 62}
        ]
        result = sorted(data, cmp=mapping_columns.sort_duplicates)

        self.assertListEqual(result, expected)
