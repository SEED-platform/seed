# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Dan Gunter <dkgunter@lbl.gov>'

Unit tests for map.py
"""

import logging

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.mappings import mapping_data
from seed.models import Column, Unit, FLOAT
from seed.utils.organizations import create_organization

_log = logging.getLogger(__name__)


class TestMappingData(TestCase):
    """Test mapping data methods."""

    def setUp(self):
        self.user = User.objects.create_superuser('test_user@demo.com', 'test_user@demo.com', 'test_pass')
        self.org, _, _ = create_organization(self.user)

    def test_mapping_data_init(self):
        # verify that the data loaded as expected
        md = mapping_data.MappingData(self.org)
        for d in md.data:
            del d['id']

        import json
        print(json.dumps(md.data, indent=2))

        expected = {
            "is_extra_data": False,
            "display_name": "Address Line 1",
            "dbName": "address_line_1",
            "data_type": "string",
            "sharedFieldType": "None",
            "table_name": "PropertyState",
            "column_name": "address_line_1"
        }
        self.assertIn(expected, md.data)

        expected = {
            "is_extra_data": False,
            "display_name": "State",
            "dbName": "state",
            "data_type": "string",
            "sharedFieldType": "None",
            "table_name": "TaxLotState",
            "column_name": "state"
        }
        self.assertIn(expected, md.data)

    def test_keys(self):
        md = mapping_data.MappingData(self.org)

        d = md.keys
        # _log.debug(d)

        print d

        # should only have one of each (3 of the fields are common in tax
        # lot and property table.

        expected_data = [
            u'address_line_1',
            u'address_line_2',
            u'block_number',
            u'building_certification',
            u'building_count',
            u'city',
            u'conditioned_floor_area',
            u'custom_id_1',
            u'district',
            u'energy_alerts',
            u'energy_score',
            u'generation_date',
            u'gross_floor_area',
            u'home_energy_score_id',
            u'jurisdiction_property_id',
            u'jurisdiction_tax_lot_id',
            u'lot_number',
            u'number_properties',
            u'occupied_floor_area',
            u'owner',
            u'owner_address',
            u'owner_city_state',
            u'owner_email',
            u'owner_postal_code',
            u'owner_telephone',
            u'pm_parent_property_id',
            u'pm_property_id',
            u'postal_code',
            u'latitude',
            u'longitude',
            u'property_name',
            u'property_notes',
            u'property_type',
            u'recent_sale_date',
            u'release_date',
            u'site_eui',
            u'site_eui_modeled',
            u'site_eui_weather_normalized',
            u'source_eui',
            u'source_eui_weather_normalized',
            u'space_alerts',
            u'state',
            u'use_description',
            u'year_built',
            u'year_ending',
            u'analysis_start_time',
            u'analysis_state_message',
            u'analysis_state',
            u'analysis_end_time',
            u'source_eui_modeled',
            u'updated',
            u'created',
            u'campus',
            u'ubid'
        ]

        # nope you can't compare a list to keys, as keys are unordered
        # self.assertListEqual(d, expected_data)

        # prevent duplicate entries in expected_data
        assert len(expected_data) == len(set(expected_data))
        # >>> set([1, 2,3]) == set ([3, 2, 1])
        self.assertEqual(set(expected_data), set(d))

    def test_find_column(self):
        md = mapping_data.MappingData(self.org)

        expect_0 = {
            'is_extra_data': False,
            'display_name': u'City',
            'dbName': u'city',
            'data_type': u'string',
            'sharedFieldType': u'None',
            'table_name': u'TaxLotState',
            'column_name': u'city'
        }
        c = md.find_column(expect_0['table_name'], expect_0['column_name'])
        del c['id']
        # _log.debug(json.dumps(c, indent=4, sort_keys=True))
        self.assertDictEqual(c, expect_0)

    def test_null_extra_data(self):
        md = mapping_data.MappingData(self.org)
        self.assertEquals(md.extra_data, [])

    def test_extra_data(self):
        # load up a bunch of columns

        Column.objects.get_or_create(organization=self.org, column_name="a_column", table_name="TaxLotState",
                                     is_extra_data=True)
        u, _ = Unit.objects.get_or_create(unit_name="faraday", unit_type=FLOAT)
        Column.objects.get_or_create(organization=self.org, column_name="z_column", table_name="PropertyState",
                                     is_extra_data=True, unit=u)
        # columns = list(Column.objects.select_related('unit').exclude(column_name__in=self.obj.keys))
        # self.obj.add_extra_data(columns)

        md = mapping_data.MappingData(self.org)

        for c in md.data:
            del c['id']

        # _log.debug(json.dumps(self.obj.data[0], indent=4, sort_keys=True))
        expected_data_0 = {
            "is_extra_data": True,
            "display_name": "A Column",
            "dbName": "a_column",
            "data_type": "None",
            "sharedFieldType": "None",
            "table_name": "TaxLotState",
            "column_name": "a_column"
        }

        expected_data_z = {
            "is_extra_data": True,
            "display_name": "Z Column",
            "dbName": "z_column",
            "data_type": "None",
            "sharedFieldType": "None",
            "table_name": "PropertyState",
            "column_name": "z_column"
        }

        # import json
        # print json.dumps(md.data, indent=2)

        # _log.debug(json.dumps(self.obj.data, indent=4, sort_keys=True))
        c = md.find_column('TaxLotState', 'a_column')
        self.assertDictEqual(c, expected_data_0)
        c = md.find_column('PropertyState', 'z_column')
        self.assertDictEqual(c, expected_data_z)
        c = md.find_column('DNE', 'z_column')
        self.assertEqual(c, None)

        expected = [expected_data_z, expected_data_0]
        c = md.extra_data
        self.assertListEqual(expected, c)
