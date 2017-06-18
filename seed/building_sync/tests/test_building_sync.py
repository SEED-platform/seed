# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

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

        self.assertEqual(self.bs.address_line_1, '123 Main Street')
        self.assertEqual(self.bs.city, 'Denver')

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
