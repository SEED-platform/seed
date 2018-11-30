# !/usr/bin/env python
# encoding: utf-8
"""
Test Geocoding of Properties and Tax Lots

On first run, HTTP request/responses are truely sent and received.
On subsequent runs on the same machine, API request/responses are
intercepted/mocked by VCR. To execute an actual HTTP request/response
(and not use mocked data), delete the vcr_cassette files.
"""

import vcr

from django.test import TestCase

from seed.landing.models import SEEDUser as User

from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState

from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory,
)

from seed.utils.geocode import geocode_addresses
from seed.utils.geocode import long_lat_wkt
from seed.utils.organizations import create_organization

# import pdb; pdb.set_trace()

class GeocodeBase(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.tax_lot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    @vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_base_case.yaml')
    def test_geocode_addresses_successful_when_real_fields_provided(self):
        property_details = self.property_state_factory.get_details()

        property_details['organization_id'] = self.org.id

        property_details['address_line_1'] = "3001 Brighton Blvd"
        property_details['address_line_2'] = "suite 2693"
        property_details['city'] = "Denver"
        property_details['state'] = "Colorado"
        property_details['postal_code'] = "80216"

        property = PropertyState(**property_details)
        property.save()

        tax_lot_details = self.tax_lot_state_factory.get_details()

        tax_lot_details['organization_id'] = self.org.id

        tax_lot_details['address_line_1'] = "2020 Lawrence St"
        tax_lot_details['address_line_2'] = "unit A"
        tax_lot_details['city'] = "Denver"
        tax_lot_details['state'] = "Colorado"
        tax_lot_details['postal_code'] = "80205"

        tax_lot = TaxLotState(**tax_lot_details)
        tax_lot.save()

        geocode_addresses([tax_lot])
        geocode_addresses([property])

        self.assertEqual('POINT (-104.985765 39.764984)', long_lat_wkt(property))
        self.assertEqual('POINT (-104.991315 39.752603)', long_lat_wkt(tax_lot))
