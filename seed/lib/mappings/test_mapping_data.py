# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author 'Dan Gunter <dkgunter@lbl.gov>'

Unit tests for map.py
"""

import logging

from django.test import TestCase

from seed.lib.mappings import mapping_data
from seed.models import Column, Unit, FLOAT

_log = logging.getLogger(__name__)


class TestMappingData(TestCase):
    """Test mapping data methods."""

    def setUp(self):
        self.maxDiff = None
        self.obj = mapping_data.MappingData()

    def test_mapping_data_init(self):
        # _log.debug(json.dumps(self.obj.data, indent=4, sort_keys=True))

        # verify that the data loaded as expected
        fake_data_0 = {
            "js_type": "",
            "name": "address_line_1",
            "schema": "BEDES",
            "table": "PropertyState",
            "type": "CharField",
            "extra_data": False,
        }
        self.assertDictEqual(fake_data_0, self.obj.data[0])

        fake_data_last = {
            "js_type": "",
            "name": "state",
            "schema": "BEDES",
            "table": "TaxLotState",
            "type": "CharField",
            "extra_data": False,
        }
        self.assertDictEqual(fake_data_last,
                             self.obj.data[len(self.obj.data) - 1])

    def test_keys(self):
        d = self.obj.keys()
        # _log.debug(d)

        # should only have one of each (3 of the fields are common in tax
        # lot and property table.
        expected_data = ['address', 'address_line_1', 'address_line_2',
                         'block_number', 'building_certification',
                         'building_count',
                         'home_energy_score_id',
                         'building_portfolio_manager_identifier', 'city',
                         'conditioned_floor_area', 'custom_id_1', 'data_state',
                         'district', 'energy_alerts', 'energy_score',
                         'generation_date', 'gross_floor_area',
                         'jurisdiction_property_id',
                         'jurisdiction_taxlot_identifier', 'lot_number',
                         'number_properties', 'occupied_floor_area', 'owner',
                         'owner_address', 'owner_city_state', 'owner_email',
                         'owner_postal_code', 'owner_telephone',
                         'pm_parent_property_id', 'pm_property_id',
                         'postal_code', 'property_name', 'property_notes',
                         'recent_sale_date', 'release_date', 'site_eui',
                         'site_eui_weather_normalized', 'source_eui',
                         'source_eui_weather_normalized', 'space_alerts',
                         'state', 'use_description', 'year_built',
                         'year_ending']
        self.assertListEqual(d, expected_data)

    def test_find_column(self):
        expect_0 = {
            "js_type": "",
            "name": "city",
            "schema": "BEDES",
            "table": "TaxLotState",
            "type": "CharField",
            "extra_data": False,
        }

        c = self.obj.find_column(expect_0['table'], expect_0['name'])

        # _log.debug(json.dumps(c, indent=4, sort_keys=True))
        self.assertDictEqual(c, expect_0)

        expect_0 = {
            "js_type": "",
            "name": "city",
            "schema": "BEDES",
            "table": "PropertyState",
            "type": "CharField",
            "extra_data": False,
        }

        c = self.obj.find_column(expect_0['table'], expect_0['name'])
        self.assertDictEqual(c, expect_0)

    def test_null_extra_data(self):
        self.assertEquals(self.obj.extra_data(), [])

    def test_extra_data(self):
        # load up a bunch of columns
        Column.objects.get_or_create(column_name="a_column", table_name="")
        u, _ = Unit.objects.get_or_create(unit_name="faraday", unit_type=FLOAT)
        Column.objects.get_or_create(column_name="z_column", table_name="PropertyState", unit=u)
        columns = list(Column.objects.select_related('unit').exclude(
            column_name__in=self.obj.keys()))

        self.obj.add_extra_data(columns)

        # _log.debug(json.dumps(self.obj.data[0], indent=4, sort_keys=True))
        expected_data_0 = {
            "extra_data": True,
            "js_type": "string",
            "name": "a_column",
            "schema": "BEDES",
            "table": "",
            "type": "string"
        }
        expected_data_z = {
            "extra_data": True,
            "js_type": "float",
            "name": "z_column",
            "schema": "BEDES",
            "table": "PropertyState",
            "type": "float"
        }

        self.assertDictEqual(self.obj.data[0], expected_data_0)

        # _log.debug(json.dumps(self.obj.data, indent=4, sort_keys=True))
        c = self.obj.find_column('', 'a_column')
        self.assertDictEqual(c, expected_data_0)
        c = self.obj.find_column('PropertyState', 'z_column')
        self.assertDictEqual(c, expected_data_z)
        c = self.obj.find_column('DNE', 'z_column')
        self.assertEqual(c, None)

        expected = [
            {
                'name': u'a_column',
                'js_type': 'string',
                'table': '',
                'extra_data': True,
                'type': 'string',
                'schema': 'BEDES'
            }, {
                'name': u'z_column',
                'js_type': u'float',
                'table': 'PropertyState',
                'extra_data': True,
                'type': u'float',
                'schema': 'BEDES'
            }
        ]
        c = self.obj.extra_data()
        self.assertListEqual(expected, c)
