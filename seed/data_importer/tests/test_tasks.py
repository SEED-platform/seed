# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed.data_importer.tasks import ALL_COMPARISON_FIELDS
from seed.data_importer.tests.util import DataMappingBaseTestCase
from seed.landing.models import SEEDUser as User


class TaskTests(DataMappingBaseTestCase):
    """
    Tests of the data_importer views (and the objects they create).
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(email='test_user@demo.com', **user_details)
        self.client.login(**user_details)

    def test_all_comparison_fields(self):
        expected = [
            'address_line_1', 'address_line_2', 'analysis_end_time', 'analysis_start_time', 'analysis_state',
            'analysis_state_message', 'block_number', 'building_certification', 'building_count', 'campus', 'city',
            'conditioned_floor_area', 'created', 'custom_id_1', 'district', 'energy_alerts', 'energy_score',
            'generation_date', 'gross_floor_area', 'home_energy_score_id', 'jurisdiction_property_id',
            'jurisdiction_tax_lot_id', 'latitude', 'longitude', 'lot_number', 'normalized_address', 'number_properties',
            'occupied_floor_area', 'owner', 'owner_address', 'owner_city_state', 'owner_email', 'owner_postal_code',
            'owner_telephone', 'parent_property', 'pm_parent_property_id', 'pm_property_id', 'postal_code',
            'property_name', 'property_notes', 'property_type', 'recent_sale_date', 'release_date', 'site_eui',
            'site_eui_modeled', 'site_eui_weather_normalized', 'source_eui', 'source_eui_modeled',
            'source_eui_weather_normalized', 'space_alerts', 'state', 'ubid', 'updated', 'use_description',
            'year_built', 'year_ending'
        ]

        self.assertListEqual(ALL_COMPARISON_FIELDS, expected)
