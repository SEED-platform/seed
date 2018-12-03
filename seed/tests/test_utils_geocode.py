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
        properties = PropertyState.objects.filter(pk=property.id)

        tax_lot_details = self.tax_lot_state_factory.get_details()
        tax_lot_details['organization_id'] = self.org.id
        tax_lot_details['address_line_1'] = "2020 Lawrence St"
        tax_lot_details['address_line_2'] = "unit A"
        tax_lot_details['city'] = "Denver"
        tax_lot_details['state'] = "Colorado"
        tax_lot_details['postal_code'] = "80205"

        tax_lot = TaxLotState(**tax_lot_details)
        tax_lot.save()
        tax_lots = TaxLotState.objects.filter(pk=tax_lot.id)

        geocode_addresses(properties)
        geocode_addresses(tax_lots)

        self.assertEqual('POINT (-104.985765 39.764984)', long_lat_wkt(properties[0]))
        self.assertEqual('POINT (-104.991315 39.752603)', long_lat_wkt(tax_lots[0]))

    @vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_low_geocodequality.yaml')
    def test_geocode_addresses_returns_no_data_when_provided_address_is_ambigious(self):
        state_zip_only_details = self.property_state_factory.get_details()
        state_zip_only_details['organization_id'] = self.org.id
        state_zip_only_details['address_line_1'] = ""
        state_zip_only_details['address_line_2'] = ""
        state_zip_only_details['city'] = ""
        state_zip_only_details['state'] = "Colorado"
        state_zip_only_details['postal_code'] = "80202"

        state_zip_only_property = PropertyState(**state_zip_only_details)
        state_zip_only_property.save()

        wrong_state_zip_details = self.property_state_factory.get_details()
        wrong_state_zip_details['organization_id'] = self.org.id
        wrong_state_zip_details['address_line_1'] = "3001 Brighton Blvd"
        wrong_state_zip_details['address_line_2'] = "suite 2693"
        wrong_state_zip_details['city'] = "Denver"
        wrong_state_zip_details['state'] = "New Jersey"
        wrong_state_zip_details['postal_code'] = "08081"

        wrong_state_zip_property = PropertyState(**wrong_state_zip_details)
        wrong_state_zip_property.save()

        ids = [state_zip_only_property.id, wrong_state_zip_property.id]

        properties = PropertyState.objects.filter(id__in=ids)

        geocode_addresses(properties)

        state_zip_only_property = PropertyState.objects.get(pk=state_zip_only_property.id)
        wrong_state_zip_property = PropertyState.objects.get(pk=wrong_state_zip_property.id)

        self.assertIsNone(state_zip_only_property.long_lat)
        self.assertIsNone(wrong_state_zip_property.long_lat)

    @vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_dup_addresses.yaml')
    def test_geocode_addresses_is_successful_even_if_two_buildings_have_same_address(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['address_line_1'] = "3001 Brighton Blvd"
        property_details['address_line_2'] = "suite 2693"
        property_details['city'] = "Denver"
        property_details['state'] = "Colorado"
        property_details['postal_code'] = "80216"

        property_1 = PropertyState(**property_details)
        property_2 = PropertyState(**property_details)
        property_1.save()
        property_2.save()

        ids = [property_1.id, property_2.id]

        properties = PropertyState.objects.filter(id__in=ids)

        geocode_addresses(properties)

        for property in properties:
            self.assertEqual('POINT (-104.985765 39.764984)', long_lat_wkt(property))

    @vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_101_unique_addresses.yaml')
    def test_geocode_addresses_is_successful_with_over_100_properties(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['address_line_2'] = ""
        property_details['city'] = "Denver"
        property_details['state'] = "Colorado"
        property_details['postal_code'] = "80202"

        ids = []
        for n in range(101):
            street_number = n + 1600
            property_details['address_line_1'] = str(street_number) + " Larimer Street"

            property = PropertyState(**property_details)
            property.save()
            ids.append(property.id)

        properties = PropertyState.objects.filter(id__in=ids)

        geocode_addresses(properties)

        long_lats = [
            property.long_lat
            for property
            in properties
            if property.long_lat is not None
        ]

        self.assertTrue(len(long_lats) > 0)
