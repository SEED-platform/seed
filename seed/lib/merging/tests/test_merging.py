# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import logging

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.lib.merging import merging
from seed.lib.merging.merging import get_state_attrs, get_state_to_state_tuple
from seed.models.columns import Column
from seed.test_helpers.fake import (
    FakePropertyViewFactory,
    FakeTaxLotViewFactory
)
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class StateFieldsTest(TestCase):
    """Tests that our logic for constructing cleaners works."""

    def setUp(self):
        self.maxDiff = None
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)

    def test_get_state_attrs(self):
        # create the column for data_1
        Column.objects.create(
            column_name='data_1',
            table_name='TaxLotState',
            organization=self.org,
            is_extra_data=True,
        )
        tlv1 = self.taxlot_view_factory.get_taxlot_view(extra_data={"data_1": "value_1"})
        tlv2 = self.taxlot_view_factory.get_taxlot_view(extra_data={"data_1": "value_2"})

        self.assertEqual(tlv1.state.extra_data['data_1'], 'value_1')
        self.assertEqual(tlv2.state.extra_data['data_1'], 'value_2')

        res = get_state_attrs([tlv1.state, tlv2.state])
        self.assertEqual(res['custom_id_1'], {tlv2.state: None, tlv1.state: None})
        self.assertEqual(res['postal_code'],
                         {tlv2.state: tlv2.state.postal_code, tlv1.state: tlv1.state.postal_code})
        self.assertTrue('data_1' not in res)

    def test_property_state(self):
        self.property_view_factory.get_property_view()
        self.taxlot_view_factory.get_taxlot_view()

        expected = (('address_line_1', 'address_line_1'),
                    ('address_line_2', 'address_line_2'),
                    ('analysis_end_time', 'analysis_end_time'),
                    ('analysis_start_time', 'analysis_start_time'),
                    ('analysis_state_message', 'analysis_state_message'),
                    ('building_certification', 'building_certification'),
                    ('building_count', 'building_count'),
                    ('city', 'city'),
                    ('conditioned_floor_area', 'conditioned_floor_area'),
                    ('custom_id_1', 'custom_id_1'),
                    ('energy_alerts', 'energy_alerts'),
                    ('energy_score', 'energy_score'),
                    ('generation_date', 'generation_date'),
                    ('gross_floor_area', 'gross_floor_area'),
                    ('home_energy_score_id', 'home_energy_score_id'),
                    ('jurisdiction_property_id', 'jurisdiction_property_id'),
                    ('latitude', 'latitude'),
                    ('longitude', 'longitude'),
                    ('lot_number', 'lot_number'),
                    ('occupied_floor_area', 'occupied_floor_area'),
                    ('owner', 'owner'),
                    ('owner_address', 'owner_address'),
                    ('owner_city_state', 'owner_city_state'),
                    ('owner_email', 'owner_email'),
                    ('owner_postal_code', 'owner_postal_code'),
                    ('owner_telephone', 'owner_telephone'),
                    ('pm_parent_property_id', 'pm_parent_property_id'),
                    ('pm_property_id', 'pm_property_id'),
                    ('postal_code', 'postal_code'),
                    ('property_footprint', 'property_footprint'),
                    ('property_name', 'property_name'),
                    ('property_notes', 'property_notes'),
                    ('property_type', 'property_type'),
                    ('recent_sale_date', 'recent_sale_date'),
                    ('release_date', 'release_date'),
                    ('site_eui', 'site_eui'),
                    ('site_eui_modeled', 'site_eui_modeled'),
                    ('site_eui_weather_normalized', 'site_eui_weather_normalized'),
                    ('source_eui', 'source_eui'),
                    ('source_eui_modeled', 'source_eui_modeled'),
                    ('source_eui_weather_normalized', 'source_eui_weather_normalized'),
                    ('space_alerts', 'space_alerts'),
                    ('state', 'state'),
                    ('ubid', 'ubid'),
                    ('use_description', 'use_description'),
                    ('year_built', 'year_built'),
                    ('year_ending', 'year_ending'))

        result = get_state_to_state_tuple('PropertyState')
        self.assertSequenceEqual(expected, result)

    def test_taxlot_state(self):
        expected = (
            ('address_line_1', 'address_line_1'),
            ('address_line_2', 'address_line_2'),
            ('block_number', 'block_number'),
            ('city', 'city'),
            ('custom_id_1', 'custom_id_1'),
            ('district', 'district'),
            ('jurisdiction_tax_lot_id', 'jurisdiction_tax_lot_id'),
            ('latitude', 'latitude'),
            ('longitude', 'longitude'),
            ('number_properties', 'number_properties'),
            ('postal_code', 'postal_code'),
            ('state', 'state'),
            ('taxlot_footprint', 'taxlot_footprint'),
            ('ulid', 'ulid'))
        result = get_state_to_state_tuple('TaxLotState')
        self.assertSequenceEqual(expected, result)

    def test_merge_state_favor_existing(self):
        pv1 = self.property_view_factory.get_property_view(
            address_line_1='original_address', address_line_2='orig',
            extra_data={'field_1': 'orig_value'}
        )
        pv2 = self.property_view_factory.get_property_view(
            address_line_1='new_address', address_line_2='new',
            extra_data={'field_1': 'new_value'}
        )

        # Do not set priority for address_line_2 to make sure that it chooses t
        column_priorities = {
            'address_line_1': 'Favor Existing', 'extra_data': {'field_1': 'Favor Existing'}
        }

        result = merging.merge_state(pv1.state, pv1.state, pv2.state, column_priorities)
        self.assertEqual(result.address_line_1, 'original_address')
        self.assertEqual(result.address_line_2, 'new')
        self.assertEqual(result.extra_data['field_1'], 'orig_value')

    def test_merge_extra_data(self):
        ed1 = {'field_1': 'orig_value_1', 'field_2': 'orig_value_1', 'field_3': 'only_in_ed1'}
        ed2 = {'field_1': 'new_value_1', 'field_2': 'new_value_2', 'field_4': 'only_in_ed2'}

        # this also tests a priority on the new field but with an existing value that doesn't exist
        # in the new data.
        priorities = {'field_1': 'Favor Existing', 'field_3': 'Favor New'}
        result = merging._merge_extra_data(ed1, ed2, priorities)
        expected = {
            'field_1': 'orig_value_1',
            'field_2': 'new_value_2',
            'field_3': 'only_in_ed1',
            'field_4': 'only_in_ed2'
        }
        self.assertDictEqual(result, expected)
