# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


class TestOrganizationViews(DataMappingBaseTestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(user)

        self.client.login(**user_details)

    def test_matching_criteria_columns_view(self):
        url = reverse('api:v3:organizations-matching-criteria-columns', args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)

        default_matching_criteria_display_names = {
            'PropertyState': [
                'address_line_1',
                'custom_id_1',
                'pm_property_id',
                'ubid',
            ],
            'TaxLotState': [
                'address_line_1',
                'custom_id_1',
                'jurisdiction_tax_lot_id',
                'ubid',
            ],
        }

        self.assertCountEqual(result['PropertyState'], default_matching_criteria_display_names['PropertyState'])
        self.assertCountEqual(result['TaxLotState'], default_matching_criteria_display_names['TaxLotState'])

    def test_matching_criteria_columns_view_with_nondefault_geocoding_columns(self):
        # Deactivate city for properties and state for taxlots
        self.org.column_set.filter(
            column_name='city',
            table_name="PropertyState"
        ).update(geocoding_order=0)
        self.org.column_set.filter(
            column_name='state',
            table_name="TaxLotState"
        ).update(geocoding_order=0)

        # Create geocoding-enabled ED_city for properties and ED_state for taxlots
        self.org.column_set.create(
            column_name='ed_city',
            is_extra_data=True,
            table_name='PropertyState',
            geocoding_order=3
        )
        self.org.column_set.create(
            column_name='ed_state',
            is_extra_data=True,
            table_name='TaxLotState',
            geocoding_order=4
        )

        url = reverse('api:v3:organizations-geocoding-columns', args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)

        default_matching_criteria_display_names = {
            'PropertyState': [
                'address_line_1',
                'address_line_2',
                'ed_city',
                'state',
                'postal_code',
            ],
            'TaxLotState': [
                'address_line_1',
                'address_line_2',
                'city',
                'ed_state',
                'postal_code',
            ],
        }

        # Specifically use assertEqual as order does matter
        self.assertEqual(result['PropertyState'], default_matching_criteria_display_names['PropertyState'])
        self.assertEqual(result['TaxLotState'], default_matching_criteria_display_names['TaxLotState'])
