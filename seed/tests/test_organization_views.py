# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.core.urlresolvers import reverse

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
        url = reverse('api:v2:organizations-matching-criteria-columns', args=[self.org.id])
        raw_result = self.client.get(url)
        result = json.loads(raw_result.content)

        default_matching_criteria_display_names = {
            'PropertyState': [
                'Address Line 1',
                'Custom ID 1',
                'PM Property ID',
                'UBID',
            ],
            'TaxLotState': [
                'Address Line 1',
                'Custom ID 1',
                'Jurisdiction Tax Lot ID',
                'ULID',
            ],
        }

        self.assertCountEqual(result['PropertyState'], default_matching_criteria_display_names['PropertyState'])
        self.assertCountEqual(result['TaxLotState'], default_matching_criteria_display_names['TaxLotState'])
