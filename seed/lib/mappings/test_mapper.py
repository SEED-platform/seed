# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Dan Gunter <dkgunter@lbl.gov>'
"""
"""
Unit tests for map.py
"""

import re

from django.test import TestCase
from seed.lib.mappings.mapper import create_column_regexes, get_pm_mapping


class TestMapper(TestCase):
    """Test mapping methods."""

    def setUp(self):
        self.test_keys = [
            "Key1",
            "KEY1",
            "key1",
            "key2",
            "has spaces",
            "has_spaces",
            "has_underscores",
            "has underscores",
            "has___underscores",
            "has  multiple     spaces",
            "has___multiple spaces",
            "normal ft2",
            "normal ft^2",
            "normal ft_",
            u"normal ft" + u'\u00B2',
        ]

        self.test_mapping_data = [
            {
                "display_name": "Value 1",
                "to_field": "value_1",
                "to_table_name": "PropertyState",
                "from_field": "Key1",
                "units": "",
                "type": "string",
                "schema": ""
            },
            {
                "display_name": "Value 2",
                "to_field": "value_2",
                "to_table_name": "PropertyState",
                "from_field": "has_spaces",
                "units": "",
                "type": "string",
                "schema": ""
            },
            {
                "display_name": "Value 3",
                "to_field": "value_3",
                "to_table_name": "PropertyState",
                "from_field": "has_underscores",
                "units": "",
                "type": "string",
                "schema": ""
            },
            {
                "display_name": "Value 4",
                "to_field": "value_4",
                "to_table_name": "PropertyState",
                "from_field": "has_multiple_spaces",
                "units": "",
                "type": "string",
                "schema": ""
            },
            {
                "display_name": "Value 5",
                "to_field": "value_5",
                "to_table_name": "PropertyState",
                "from_field": "normal_ft2",
                "units": "",
                "type": "string",
                "schema": ""
            }

        ]

    def test_column_regexes(self):
        # test the cleaning of the compared columns
        columns = create_column_regexes(self.test_keys)

        self.assertListEqual([c['raw'] for c in columns], self.test_keys)
        self.assertTrue(isinstance(columns[0]['regex'], re._pattern_type))

    def test_mapping(self):
        mapping = get_pm_mapping(self.test_keys, mapping_data=self.test_mapping_data)

        # casing
        self.assertEqual(mapping['Key1'], ('PropertyState', 'value_1', 100))
        self.assertEqual(mapping['key1'], ('PropertyState', 'value_1', 100))
        self.assertEqual(mapping['KEY1'], ('PropertyState', 'value_1', 100))

        # spaces and underscores
        self.assertEqual(mapping['has spaces'], ('PropertyState', 'value_2', 100))
        self.assertEqual(mapping['has_spaces'], ('PropertyState', 'value_2', 100))
        self.assertEqual(mapping['has underscores'], ('PropertyState', 'value_3', 100))
        self.assertEqual(mapping['has___underscores'], ('PropertyState', 'value_3', 100))
        self.assertEqual(mapping['has  multiple     spaces'], ('PropertyState', 'value_4', 100))
        self.assertEqual(mapping['has___multiple spaces'], ('PropertyState', 'value_4', 100))

        # superscripts
        self.assertEqual(mapping['normal ft2'], ('PropertyState', 'value_5', 100))
        self.assertEqual(mapping['normal ft^2'], ('PropertyState', 'value_5', 100))
        self.assertEqual(mapping['normal ft_'], ('PropertyState', 'value_5', 100))
        self.assertEqual(mapping[u"normal ft" + u'\u00B2'], ('PropertyState', 'value_5', 100))

    def test_mapping_pm_to_seed(self):
        from_columns = [
            "Address 1",
            "Address_1",
            "Property ID",
            "Portfolio Manager Property ID",
            "some_other_field_not_in_the_designated_PM_mapping",
            "site eui",
            "site Eui (kBTU/ft2)",
            "site EUI",
        ]
        pm = get_pm_mapping(from_columns, resolve_duplicates=False)

        expected = {
            'Address 1': (u'PropertyState', u'address_line_1', 100),
            'Address_1': (u'PropertyState', u'address_line_1', 100),
            'Property ID': (u'PropertyState', u'pm_property_id', 100),
            'Portfolio Manager Property ID': (u'PropertyState', u'pm_property_id', 100),
            'site eui': (u'PropertyState', u'site_eui', 100),
            'site Eui (kBTU/ft2)': (u'PropertyState', u'site_eui', 100),
            'site EUI': (u'PropertyState', u'site_eui', 100)
        }
        self.assertDictEqual(pm, expected)

        pm = get_pm_mapping(from_columns, resolve_duplicates=True)
        expected = {
            'Address 1': (u'PropertyState', u'address_line_1', 100),
            'Address_1': (u'PropertyState', u'address_line_1_1', 100),
            'Property ID': (u'PropertyState', u'pm_property_id', 100),
            'Portfolio Manager Property ID': (u'PropertyState', u'pm_property_id_1', 100),
            'site eui': (u'PropertyState', u'site_eui', 100),
            'site Eui (kBTU/ft2)': (u'PropertyState', u'site_eui_1', 100),
            'site EUI': (u'PropertyState', u'site_eui_2', 100)
        }

        self.assertDictEqual(pm, expected)
        pm = get_pm_mapping(from_columns)
        self.assertDictEqual(pm, expected)
