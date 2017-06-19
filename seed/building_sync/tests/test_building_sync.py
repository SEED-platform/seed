# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

import copy
from os import path

from django.test import TestCase

from seed.building_sync.building_sync import BuildingSync


class TestBuildingSync(TestCase):
    def setUp(self):
        self.xml_file = path.join(path.dirname(__file__), 'data', 'ex_1.xml')
        self.bs = BuildingSync()

    def tearDown(self):
        pass

    def test_constructor(self):
        with self.assertRaisesRegexp(Exception, "File not found: .*"):
            self.bs.import_file('no/path/to/file.xml')

        self.assertTrue(self.bs.import_file(self.xml_file))

        expected_address = {'city': u'Denver', 'state': u'CO', 'address_line_1': u'123 Main Street'}
        self.assertDictEqual(self.bs.address, expected_address)

    def test_get_node(self):
        data = {
            "a": 1,
            "c": {
                "d": 2
            },
            "d": {
                "e": {
                    "f": {
                        "g": {
                            "h": "deep"
                        }
                    }
                }
            },
            "f": {
                "list": [
                    {"e": 1, "f": 2, "g": {"h": 27, "i": {"value": 33}}},
                    {"e": 3, "f": 4, "g": {"h": 54, "i": {"value": 66}}},
                ]
            },
            "g": [
                {
                    "list_1": [
                        {
                            "list_2": [
                                {"value": 27},
                                {"value": 54},
                            ]
                        },
                        {
                            "list_2": [
                                {"value": 99},
                                {"value": "100"},
                                {"value_2": "new"}
                            ]
                        }
                    ]
                }
            ]
        }
        result = self.bs._get_node('', data, [])
        self.assertDictEqual(data, result)

        result = self.bs._get_node('a', data, [])
        self.assertEqual(result, 1)

        result = self.bs._get_node('c', data, [])
        self.assertDictEqual(result, {"d": 2})

        result = self.bs._get_node('c.d', data, [])
        self.assertEqual(result, 2)

        result = self.bs._get_node('d.e.f.g.h', data, [])
        self.assertEqual(result, 'deep')

        result = self.bs._get_node('f.list', data, [])
        self.assertEqual(result, data['f']['list'])

        result = self.bs._get_node('f.list.e', data, [])
        self.assertEqual(result, [1, 3])

        result = self.bs._get_node('f.list.g.h', data, [])
        self.assertEqual(result, [27, 54])

        result = self.bs._get_node('f.list.g.i.value', data, [])
        self.assertEqual(result, [33, 66])

        result = self.bs._get_node('f.list.g.i.value', data, [])
        self.assertEqual(result, [33, 66])

        result = self.bs._get_node('g.list_1.list_2.value', data, [])
        self.assertEqual(result, [27, 54, 99, "100"])

        result = self.bs._get_node('g.list_1.list_2.value_2', data, [])
        self.assertEqual(result, "new")

        result = self.bs._get_node('c.d.e.f.g.h.i', data, [])
        self.assertEqual(result, None)

    def test_get_address_missing_field(self):
        self.assertTrue(self.bs.import_file(self.xml_file))

        struct = copy.copy(BuildingSync.ADDRESS_STRUCT)
        struct['return']['bungalow_name'] = {
            "path": "BungalowName",
            "required": True,
            "type": "string",
        }

        expected = {'city': u'Denver', 'state': u'CO', 'address_line_1': u'123 Main Street'}

        res, errors, mess = self.bs._process_struct(struct, self.bs.data)
        self.assertTrue(errors)
        self.assertEqual(mess, ["Could not find 'Audits.Audit.Sites.Site.Address.BungalowName'"])
        self.assertEqual(res, expected)

        # Missing path
        struct['return']['bungalow_name'] = {
            "path": "Long.List.A.B",
            "required": True,
            "type": "string",
        }
        res, errors, mess = self.bs._process_struct(struct, self.bs.data)
        self.assertTrue(errors)
        self.assertEqual(mess, ["Could not find 'Audits.Audit.Sites.Site.Address.Long.List.A.B'"])
        self.assertEqual(res, expected)

    def test_bricr_struct(self):
        self.assertTrue(self.bs.import_file(self.xml_file))
        self.maxDiff = None

        struct = copy.copy(BuildingSync.BRICR_STRUCT)
        expected = {
            'address_line_1': '123 Main Street',
            'city': 'Denver',
            'state': 'CO',
            'latitude': 40.762235027074865,
            'longitude': -121.41677258249452,
            'facility_id': 'Building991',
            'year_of_construction': 1990,
            'floors_above_grade': 1,
            'floors_below_grade': 0,
            'gross_floor_area': 25000,
            'occupancy_type': 'PDR',
            'premise_identifier': 'XY8198732',
            'property_type': 'Commercial',
        }

        res, errors, mess = self.bs._process_struct(struct, self.bs.data)
        self.assertEqual(res, expected)
        self.assertFalse(errors)
        self.assertEqual(mess, [])
