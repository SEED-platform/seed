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

from django.contrib.gis.geos import Point

from django.conf import settings

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
from seed.utils.geocode import MapQuestAPIKeyError

from seed.utils.organizations import create_organization


def batch_request_uri_length_matcher(r1, r2):
    return len(r1.uri) == len(r2.uri)


base_vcr = vcr.VCR()
batch_vcr = vcr.VCR()
batch_vcr.register_matcher('uri_length', batch_request_uri_length_matcher)


class LongLatWkt(TestCase):
    def test_long_lat_wkt_takes_a_state_and_returns_the_WKT_string_or_None(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        org, _, _ = create_organization(user)
        property_state_factory = FakePropertyStateFactory(organization=org)

        property_details = property_state_factory.get_details()
        property_details['organization_id'] = org.id

        no_long_lat_property = PropertyState(**property_details)
        no_long_lat_property.save()

        property_details['long_lat'] = 'POINT (-104.985765 39.764984)'

        geocoded_property = PropertyState(**property_details)
        geocoded_property.save()

        no_long_lat_record = PropertyState.objects.get(pk=no_long_lat_property.id)
        geocoded_record = PropertyState.objects.get(pk=geocoded_property.id)

        self.assertIsNone(no_long_lat_record.long_lat)
        self.assertIsNone(long_lat_wkt(no_long_lat_record))

        self.assertIsInstance(geocoded_record.long_lat, Point)
        self.assertEqual('POINT (-104.985765 39.764984)', long_lat_wkt(geocoded_property))


class GeocodeAddresses(TestCase):
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

    def test_geocode_addresses_successful_when_real_fields_provided(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_base_case.yaml', filter_query_parameters=['key']):
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

            refreshed_properties = PropertyState.objects.filter(pk=property.id)
            refreshed_tax_lots = TaxLotState.objects.filter(pk=tax_lot.id)

            self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_properties[0]))
            self.assertEqual('POINT (-104.991046 39.752396)', long_lat_wkt(refreshed_tax_lots[0]))

    def test_geocode_addresses_returns_no_data_when_provided_address_is_ambigious(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_low_geocodequality.yaml', filter_query_parameters=['key']):
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

    def test_geocode_addresses_is_successful_even_if_two_buildings_have_same_address(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_dup_addresses.yaml', filter_query_parameters=['key']):
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

            refreshed_properties = PropertyState.objects.filter(id__in=ids)

            for property in refreshed_properties:
                self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(property))

    def test_geocode_addresses_is_successful_with_over_100_properties(self):
        with batch_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_101_unique_addresses.yaml', match_on=['uri_length'], filter_query_parameters=['key']):
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

            properties = PropertyState.objects.filter(id__in=ids).order_by('id')

            geocode_addresses(properties)

            refreshed_properties = PropertyState.objects.filter(id__in=ids).order_by('id')

            long_lats = [
                property.long_lat
                for property
                in refreshed_properties
                if property.long_lat is not None
            ]

            self.assertTrue(len(long_lats) > 0)

    def test_geocode_addresses_is_unsuccessful_when_the_API_key_is_invalid_or_expired(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_invalid_or_expired_key.yaml'):
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

            with self.settings(MAPQUEST_API_KEY = "fakeapikey"):
                with self.assertRaises(MapQuestAPIKeyError):
                    geocode_addresses(properties)
