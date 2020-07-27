# !/usr/bin/env python
# encoding: utf-8

import ast

from django.urls import reverse

from seed.data_importer.utils import kbtu_thermal_conversion_factors
from seed.landing.models import SEEDUser as User
from seed.utils.organizations import create_organization
from seed.tests.util import DataMappingBaseTestCase


class TestMeterValidTypesUnits(DataMappingBaseTestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**self.user_details)

    def test_view_that_returns_valid_types_and_units_for_meters(self):
        url = reverse('api:v3:meters-valid-types-units')

        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            type: list(units.keys())
            for type, units
            in kbtu_thermal_conversion_factors("US").items()
        }

        self.assertEqual(result_dict, expectation)
