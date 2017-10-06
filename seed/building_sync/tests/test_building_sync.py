# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

import copy
from os import path, remove

from django.test import TestCase

from seed.building_sync.building_sync import BuildingSync
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import (
    Organization,
    OrganizationUser,
)
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
)


class TestBuildingSync(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details)
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        self.xml_file = path.join(path.dirname(__file__), 'data', 'ex_1.xml')
        self.bs = BuildingSync()

    def tearDown(self):
        pass

    def test_constructor(self):
        with self.assertRaisesRegexp(Exception, "File not found: .*"):
            self.bs.import_file('no/path/to/file.xml')

        self.assertTrue(self.bs.import_file(self.xml_file))

    def test_export_no_property(self):
        self.bs.import_file(self.xml_file)
        xml = self.bs.export(None, BuildingSync.BRICR_STRUCT)

        # save the file to disk, then reload and check if the two are the same
        new_file = path.join(path.dirname(__file__), 'data', 'test_file.xml')
        if path.exists(new_file):
            remove(new_file)

        with open(new_file, "w") as f:
            f.write(xml)

        new_bs = BuildingSync()
        new_bs.import_file(new_file)

        self.assertEqual(self.bs.raw_data, new_bs.raw_data)

    def test_export(self):
        self.bs.import_file(self.xml_file)

        # create a propertystate
        self.property_state_factory = FakePropertyStateFactory(
            organization=self.org
        )

        ps = self.property_state_factory.get_property_state(organization=self.org)
        ps.extra_data['floors_below_grade'] = 11235
        ps.save()

        xml = self.bs.export(ps, BuildingSync.BRICR_STRUCT)

        self.assertTrue("<auc:FloorsBelowGrade>11235</auc:FloorsBelowGrade>" in xml)
        self.assertTrue("<auc:State>Oregon</auc:State>" in xml)

        # check for complicated fields and measures.

    def test_set_node(self):
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
            }
        }

        result = self.bs._set_node('', data, 1999)
        self.assertFalse(result)

        result = self.bs._set_node('a', data, 1999)
        self.assertTrue(result)
        self.assertEqual(data["a"], 1999)

        result = self.bs._set_node('c.d', data, "string_me")
        self.assertTrue(result)
        self.assertEqual(data["c"]["d"], "string_me")

        result = self.bs._set_node('new', data, "new_field")
        self.assertTrue(result)
        self.assertEqual(data["new"], "new_field")

        # If setting the node before the end of the existing hash, then it will remove the rest
        result = self.bs._set_node('d.e.f.g', data, 1.234)
        self.assertTrue(result)
        self.assertEqual(data["d"]["e"]["f"]["g"], 1.234)

        # recursive create
        result = self.bs._set_node('x.y.z', data, "newest_field")
        self.assertTrue(result)
        self.assertEqual(data["x"]["y"]["z"], "newest_field")

    def test_set_node_delete(self):
        data = {
            "a": 1,
            "c": {"d": 2}
        }
        result = self.bs._set_node('c', data, None)
        self.assertTrue(result)
        self.assertTrue("c" not in data)

    def test_compound_set(self):
        data = {
            "root": {
                "a": {
                    "key": "floor_area",
                    "value": 1
                },
                "energy": [
                    {
                        "key": "eui",
                        "value": 2
                    },
                    {
                        "key": "kw",
                        "value": 3
                    }
                ]
            }
        }
        result = self.bs._set_compound_node("root.a", data, "key", "floor_area", "value", 1000)
        self.assertTrue(result)
        self.assertTrue(data["root"]["a"]["value"], 1000)

        result = self.bs._set_compound_node("root.energy", data, "key", "eui", "value", 2000)
        self.assertTrue(result)
        self.assertTrue(data["root"]["energy"][0]["value"], 2000)

        result = self.bs._set_compound_node("root.energy", data, "key", "kw", "value", 3000)
        self.assertTrue(result)
        self.assertTrue(data["root"]["energy"][1]["value"], 3000)

        result = self.bs._set_compound_node("root.energy", data, "key", "source", "value", 4000)
        self.assertTrue(result)
        self.assertEqual(len(data["root"]["energy"]), 3)
        for d in data["root"]["energy"]:
            if d["key"] == "source":
                self.assertEqual(d["value"], 4000)

        result = self.bs._set_compound_node("root.a", data, "key", "roof_area", "value", 5000)
        self.assertTrue(result)
        self.assertEqual(len(data["root"]["a"]), 2)
        for d in data["root"]["a"]:
            if d["key"] == "roof_area":
                self.assertEqual(d["value"], 5000)
            if d["key"] == "floor_area":
                self.assertEqual(d["value"], 1000)

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
        self.assertEqual(result, [])

    def test_get_address_missing_field(self):
        self.assertTrue(self.bs.import_file(self.xml_file))

        struct = copy.copy(BuildingSync.ADDRESS_STRUCT)
        struct['return']['bungalow_name'] = {
            "path": "BungalowName",
            "required": True,
            "type": "string",
        }

        expected = {
            'city': 'Denver',
            'state': 'CO',
            'address_line_1': '123 Main Street',
            'measures': [],
            'scenarios': [],
        }

        res, errors, mess = self.bs.process(struct)
        self.assertEqual(res, expected)
        self.assertTrue(errors)
        self.assertEqual(mess, [
            "Could not find required value for 'auc:Audits.auc:Audit.auc:Sites.auc:Site.auc:Address.BungalowName'"])

        # Missing path
        struct['return']['bungalow_name'] = {
            "path": "Long.List.A.B",
            "required": True,
            "type": "string",
        }
        res, errors, mess = self.bs.process(struct)
        self.assertTrue(errors)
        self.assertEqual(mess, [
            "Could not find required value for 'auc:Audits.auc:Audit.auc:Sites.auc:Site.auc:Address.Long.List.A.B'"])
        self.assertEqual(res, expected)

    def test_bricr_struct(self):
        self.assertTrue(self.bs.import_file(self.xml_file))
        self.maxDiff = None

        struct = copy.copy(BuildingSync.BRICR_STRUCT)
        expected = {
            'address_line_1': '123 Main Street',
            'city': 'Denver',
            'state': 'CO',
            'custom_id_1': 'e6a5de56-8234-4b4f-ba10-6af0ae612fd1',
            'latitude': 40.762235027074865,
            'longitude': -121.41677258249452,
            'year_built': 1990,
            'floors_above_grade': 1,
            'floors_below_grade': 0,
            'gross_floor_area': 25000.0,
            'net_floor_area': 22500.0,
            'occupancy_type': 'PDR',
            'premise_identifier': 'XY8198732',
            'property_type': 'Commercial',
            'property_name': 'Building991',
            'measures': [],
            'scenarios': [],
        }

        res, errors, mess = self.bs.process(struct)
        self.assertDictEqual(res, expected)
        self.assertFalse(errors)
        # self.assertEqual(mess, expected)
