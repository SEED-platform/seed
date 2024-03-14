# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

Test Geocoding of Properties and Tax Lots

On first run, HTTP request/responses are truly sent and received.
On subsequent runs on the same machine, API request/responses are
intercepted/mocked by VCR. To execute an actual HTTP request/response
(and not use mocked data), delete the vcr_cassette files.
"""
import vcr
from django.conf import settings
from django.contrib.gis.geos import Point, Polygon
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.utils.geocode import (
    MapQuestAPIKeyError,
    bounding_box_wkt,
    geocode_buildings,
    long_lat_wkt
)
from seed.utils.organizations import create_organization


def batch_request_uri_length_matcher(r1, r2):
    return len(r1.uri) == len(r2.uri)


def scrub_key_from_response(key=''):
    bytes_key = key.encode('utf-8')

    def before_record_response(response):
        response['body']['string'] = response['body']['string'].replace(bytes_key, b'key')
        return response
    return before_record_response


test_key = settings.TESTING_MAPQUEST_API_KEY or "placeholder"

base_vcr = vcr.VCR(
    filter_query_parameters=['key'],
    before_record_response=scrub_key_from_response(test_key)
)
batch_vcr = base_vcr
batch_vcr.register_matcher('uri_length', batch_request_uri_length_matcher)


class WktTests(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def test_long_lat_wkt_takes_a_state_and_returns_the_WKT_string_or_None(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

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

    def test_bounding_box_wkt_takes_a_state_and_returns_the_WKT_string_or_None(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

        no_bounding_box_property = PropertyState(**property_details)
        no_bounding_box_property.save()

        property_details['bounding_box'] = 'POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))'

        bounding_box_property = PropertyState(**property_details)
        bounding_box_property.save()

        no_bounding_box_record = PropertyState.objects.get(pk=no_bounding_box_property.id)
        geocoded_record = PropertyState.objects.get(pk=bounding_box_property.id)

        self.assertIsNone(no_bounding_box_record.bounding_box)
        self.assertIsNone(bounding_box_wkt(no_bounding_box_record))

        self.assertIsInstance(geocoded_record.bounding_box, Polygon)
        self.assertEqual('POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))', bounding_box_wkt(bounding_box_property))


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
        self.org.mapquest_api_key = test_key
        self.org.save()

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.tax_lot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_geocode_buildings_successful_when_real_fields_provided(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_base_case.yaml'):
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

            geocode_buildings(properties)
            geocode_buildings(tax_lots)

            refreshed_property = PropertyState.objects.get(pk=property.id)
            refreshed_tax_lot = TaxLotState.objects.get(pk=tax_lot.id)

            self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_property))
            self.assertEqual('High (P1AAA)', refreshed_property.geocoding_confidence)
            self.assertEqual(-104.986138, refreshed_property.longitude)
            self.assertEqual(39.765251, refreshed_property.latitude)

            self.assertEqual('POINT (-104.991205 39.75251)', long_lat_wkt(refreshed_tax_lot))
            self.assertEqual('High (P1AAA)', refreshed_tax_lot.geocoding_confidence)

    def test_geocode_properties_with_custom_fields(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_property_custom_fields.yaml'):
            property_details = self.property_state_factory.get_details()
            property_details['organization_id'] = self.org.id
            property_details['pm_parent_property_id'] = "3001 Brighton Blvd"
            property_details['pm_property_id'] = "suite 2693"
            property_details['property_name'] = None  # can handle empty DB col
            property_details['state'] = "Colorado"
            property_details['extra_data'] = {
                'ed_city': "Denver",
                'ed_zip': 80216,  # can handle numbers
                'ed_empty': None,  # can handle empty extra_data col
            }

            property = PropertyState(**property_details)
            property.save()
            properties = PropertyState.objects.filter(pk=property.id)

            # Activate and order geocoding columns
            self.org.column_set.filter(
                column_name='pm_parent_property_id',
                table_name="PropertyState"
            ).update(geocoding_order=1)
            self.org.column_set.filter(
                column_name='pm_property_id',
                table_name="PropertyState"
            ).update(geocoding_order=2)
            self.org.column_set.create(
                column_name='ed_city',
                is_extra_data=True,
                table_name='PropertyState',
                geocoding_order=3
            )
            self.org.column_set.filter(
                column_name='state',
                table_name="PropertyState"
            ).update(geocoding_order=4)
            self.org.column_set.create(
                column_name='ed_zip',
                is_extra_data=True,
                table_name='PropertyState',
                geocoding_order=5
            )
            self.org.column_set.create(
                column_name='ed_empty',
                is_extra_data=True,
                table_name='PropertyState',
                geocoding_order=6
            )
            self.org.column_set.filter(
                column_name='property_name',
                table_name="PropertyState"
            ).update(geocoding_order=7)

            # Deactivate default geocoding columns
            self.org.column_set.filter(
                column_name__in=['address_line_1', 'address_line_2', 'city', 'postal_code'],
                table_name="PropertyState"
            ).update(geocoding_order=0)

            geocode_buildings(properties)

            refreshed_property = PropertyState.objects.get(pk=property.id)

            self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_property))
            self.assertEqual('High (P1AAA)', refreshed_property.geocoding_confidence)
            self.assertEqual(-104.986138, refreshed_property.longitude)
            self.assertEqual(39.765251, refreshed_property.latitude)

    def test_geocode_taxlots_with_custom_fields(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_taxlots_custom_fields.yaml'):
            taxlot_details = self.tax_lot_state_factory.get_details()
            taxlot_details['organization_id'] = self.org.id
            taxlot_details['jurisdiction_tax_lot_id'] = "3001 Brighton Blvd"
            taxlot_details['block_number'] = "suite 2693"
            taxlot_details['custom_id_1'] = None  # can handle empty DB col
            taxlot_details['state'] = "Colorado"
            taxlot_details['extra_data'] = {
                'ed_city': "Denver",
                'ed_zip': 80216,  # can handle numbers
                'ed_empty': None,  # can handle empty extra_data col
            }

            taxlot = TaxLotState(**taxlot_details)
            taxlot.save()
            taxlots = TaxLotState.objects.filter(pk=taxlot.id)

            # Activate and order geocoding columns
            self.org.column_set.filter(
                column_name='jurisdiction_tax_lot_id',
                table_name="TaxLotState"
            ).update(geocoding_order=1)
            self.org.column_set.filter(
                column_name='block_number',
                table_name="TaxLotState"
            ).update(geocoding_order=2)
            self.org.column_set.create(
                column_name='ed_city',
                is_extra_data=True,
                table_name='TaxLotState',
                geocoding_order=3
            )
            self.org.column_set.filter(
                column_name='state',
                table_name="TaxLotState"
            ).update(geocoding_order=4)
            self.org.column_set.create(
                column_name='ed_zip',
                is_extra_data=True,
                table_name='TaxLotState',
                geocoding_order=5
            )
            self.org.column_set.create(
                column_name='ed_empty',
                is_extra_data=True,
                table_name='TaxLotState',
                geocoding_order=6
            )
            self.org.column_set.filter(
                column_name='custom_id_1',
                table_name="TaxLotState"
            ).update(geocoding_order=7)

            # Deactivate default geocoding columns
            self.org.column_set.filter(
                column_name__in=['address_line_1', 'address_line_2', 'city', 'postal_code'],
                table_name="TaxLotState"
            ).update(geocoding_order=0)

            geocode_buildings(taxlots)

            refreshed_taxlot = TaxLotState.objects.get(pk=taxlot.id)

            self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_taxlot))
            self.assertEqual('High (P1AAA)', refreshed_taxlot.geocoding_confidence)
            self.assertEqual(-104.986138, refreshed_taxlot.longitude)
            self.assertEqual(39.765251, refreshed_taxlot.latitude)

    def test_not_enough_geocoding_fields_for_org_leads_to_no_geocoding(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['address_line_1'] = "3001 Brighton Blvd"
        property_details['address_line_2'] = "suite 2693"
        property_details['city'] = "Denver"
        property_details['state'] = "Colorado"
        property_details['postal_code'] = "80216"

        # Deactivate all PropertyState geocoding columns
        self.org.column_set.filter(
            table_name="PropertyState"
        ).update(geocoding_order=0)

        property = PropertyState(**property_details)
        property.save()
        properties = PropertyState.objects.filter(pk=property.id)

        self.assertIsNone(geocode_buildings(properties))

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertIsNone(refreshed_property.long_lat)
        self.assertIsNone(refreshed_property.geocoding_confidence)

    def test_not_enough_geocoding_fields_for_record_leads_to_no_geocoding(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['address_line_1'] = ""
        property_details['address_line_2'] = ""
        property_details['city'] = ""
        property_details['state'] = ""
        property_details['postal_code'] = ""

        property = PropertyState(**property_details)
        property.save()
        properties = PropertyState.objects.filter(pk=property.id)

        self.assertIsNone(geocode_buildings(properties))

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertIsNone(refreshed_property.long_lat)
        self.assertEqual(refreshed_property.geocoding_confidence, "Missing address components (N/A)")

    def test_geocode_buildings_returns_no_data_when_provided_address_is_ambiguous(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_low_geocodequality.yaml'):
            # 1st Property
            state_zip_only_details = self.property_state_factory.get_details()
            state_zip_only_details['organization_id'] = self.org.id
            state_zip_only_details['address_line_1'] = ""
            state_zip_only_details['address_line_2'] = ""
            state_zip_only_details['city'] = ""
            state_zip_only_details['state'] = "Colorado"
            state_zip_only_details['postal_code'] = "80202"

            state_zip_only_property = PropertyState(**state_zip_only_details)
            state_zip_only_property.save()

            properties = PropertyState.objects.filter(id__in=[state_zip_only_property.id])

            geocode_buildings(properties)

            state_zip_only_property = PropertyState.objects.get(pk=state_zip_only_property.id)

            self.assertIsNone(state_zip_only_property.long_lat)
            self.assertIsNone(state_zip_only_property.longitude)
            self.assertIsNone(state_zip_only_property.latitude)
            self.assertEqual("Low - check address (Z1XAA)", state_zip_only_property.geocoding_confidence)

            # 2nd Property
            wrong_state_zip_details = self.property_state_factory.get_details()
            wrong_state_zip_details['organization_id'] = self.org.id
            wrong_state_zip_details['address_line_1'] = ""
            wrong_state_zip_details['address_line_2'] = ""
            wrong_state_zip_details['city'] = "Denver"
            wrong_state_zip_details['state'] = "Colorado"
            wrong_state_zip_details['postal_code'] = ""

            wrong_state_zip_property = PropertyState(**wrong_state_zip_details)
            wrong_state_zip_property.save()

            properties = PropertyState.objects.filter(id__in=[wrong_state_zip_property.id])

            geocode_buildings(properties)

            wrong_state_zip_property = PropertyState.objects.get(pk=wrong_state_zip_property.id)

            self.assertIsNone(wrong_state_zip_property.long_lat)
            self.assertIsNone(wrong_state_zip_property.longitude)
            self.assertIsNone(wrong_state_zip_property.latitude)
            self.assertEqual("Low - check address (A5XAX)", wrong_state_zip_property.geocoding_confidence)

    def test_geocode_buildings_returns_no_data_when_provided_address_returns_multiple_results(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_multiple_results.yaml'):
            # 1st Property
            wrong_state_details = self.property_state_factory.get_details()
            wrong_state_details['organization_id'] = self.org.id
            wrong_state_details['address_line_1'] = "101 Market Street"
            wrong_state_details['address_line_2'] = ""
            wrong_state_details['city'] = "Denver"
            wrong_state_details['state'] = "California"
            wrong_state_details['postal_code'] = ""

            wrong_state_property = PropertyState(**wrong_state_details)
            wrong_state_property.save()

            properties = PropertyState.objects.filter(id__in=[wrong_state_property.id])

            geocode_buildings(properties)

            wrong_state_property = PropertyState.objects.get(pk=wrong_state_property.id)

            self.assertIsNone(wrong_state_property.long_lat)
            self.assertIsNone(wrong_state_property.longitude)
            self.assertIsNone(wrong_state_property.latitude)
            self.assertEqual("Low - check address (Ambiguous)", wrong_state_property.geocoding_confidence)

            # 2nd Property
            not_specific_enough_details = self.property_state_factory.get_details()
            not_specific_enough_details['organization_id'] = self.org.id
            not_specific_enough_details['address_line_1'] = "101 Market Street"
            not_specific_enough_details['address_line_2'] = ""
            not_specific_enough_details['city'] = ""
            not_specific_enough_details['state'] = "California"
            not_specific_enough_details['postal_code'] = ""

            not_specific_enough_property = PropertyState(**not_specific_enough_details)
            not_specific_enough_property.save()

            properties = PropertyState.objects.filter(id__in=[not_specific_enough_property.id])

            geocode_buildings(properties)

            not_specific_enough_property = PropertyState.objects.get(pk=not_specific_enough_property.id)

            self.assertIsNone(not_specific_enough_property.long_lat)
            self.assertIsNone(not_specific_enough_property.longitude)
            self.assertIsNone(not_specific_enough_property.latitude)
            self.assertEqual("Low - check address (Ambiguous)", not_specific_enough_property.geocoding_confidence)

    def test_geocode_buildings_is_successful_even_if_two_buildings_have_same_address(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_dup_addresses.yaml'):
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

            geocode_buildings(properties)

            refreshed_properties = PropertyState.objects.filter(id__in=ids)

            for property in refreshed_properties:
                self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(property))
                self.assertEqual('High (P1AAA)', property.geocoding_confidence)
                self.assertEqual(-104.986138, property.longitude)
                self.assertEqual(39.765251, property.latitude)

    def test_geocode_buildings_is_successful_with_over_100_properties(self):
        with batch_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_101_unique_addresses.yaml', match_on=['uri_length']):
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

            geocode_buildings(properties)

            refreshed_properties = PropertyState.objects.filter(id__in=ids).order_by('id')

            long_lats = [
                property.long_lat
                for property
                in refreshed_properties
                if property.long_lat is not None
            ]
            geocode_confidence_results = [
                property.geocoding_confidence
                for property
                in refreshed_properties
                if property.geocoding_confidence is not None
            ]

            self.assertTrue(len(long_lats) > 0)
            self.assertTrue(len(geocode_confidence_results) == 101)

    def test_geocode_buildings_is_unsuccessful_when_the_API_key_is_invalid_or_expired(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_invalid_or_expired_key.yaml'):
            self.org_fake_key, _, _ = create_organization(self.user)
            self.org_fake_key.mapquest_api_key = 'fakeapikey'
            self.org_fake_key.save()

            self.property_state_factory_fake_key = FakePropertyStateFactory(organization=self.org_fake_key)

            property_details_fake_key = self.property_state_factory_fake_key.get_details()
            property_details_fake_key['organization_id'] = self.org_fake_key.id
            property_details_fake_key['address_line_1'] = "3001 Brighton Blvd"
            property_details_fake_key['address_line_2'] = "suite 2693"
            property_details_fake_key['city'] = "Denver"
            property_details_fake_key['state'] = "Colorado"
            property_details_fake_key['postal_code'] = "80216"

            property = PropertyState(**property_details_fake_key)
            property.save()

            properties = PropertyState.objects.filter(pk=property.id)

            with self.assertRaises(MapQuestAPIKeyError):
                geocode_buildings(properties)

    def test_geocode_buildings_doesnt_run_an_api_request_when_an_API_key_is_not_provided(self):
        self.org_no_key, _, _ = create_organization(self.user)
        self.property_state_factory_no_key = FakePropertyStateFactory(organization=self.org_no_key)
        property_details_no_key = self.property_state_factory_no_key.get_details()

        property_details_no_key['organization_id'] = self.org_no_key.id
        property_details_no_key['address_line_1'] = "3001 Brighton Blvd"
        property_details_no_key['address_line_2'] = "suite 2693"
        property_details_no_key['city'] = "Denver"
        property_details_no_key['state'] = "Colorado"
        property_details_no_key['postal_code'] = "80216"

        property = PropertyState(**property_details_no_key)
        property.save()

        properties = PropertyState.objects.filter(pk=property.id)

        self.assertIsNone(geocode_buildings(properties))

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertIsNone(refreshed_property.long_lat)
        self.assertIsNone(refreshed_property.geocoding_confidence)

    def test_geocode_address_can_handle_addresses_with_reserved_and_unsafe_characters(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_reserved_and_unsafe_characters.yaml'):
            property_details = self.property_state_factory.get_details()
            property_details['organization_id'] = self.org.id
            property_details['address_line_1'] = r'3001 Brighton Blvd;/?:@=&<>#%{}|"\^~[]`'
            property_details['address_line_2'] = "suite 2693"
            property_details['city'] = "Denver"
            property_details['state'] = "Colorado"
            property_details['postal_code'] = "80216"

            property = PropertyState(**property_details)
            property.save()

            properties = PropertyState.objects.filter(pk=property.id)

            geocode_buildings(properties)

            refreshed_properties = PropertyState.objects.filter(pk=property.id)

            self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_properties[0]))

    def test_geocode_address_can_use_prepopulated_lat_and_long_fields(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['latitude'] = 39.765251
        property_details['longitude'] = -104.986138

        property = PropertyState(**property_details)
        property.save()

        properties = PropertyState.objects.filter(pk=property.id)

        geocode_buildings(properties)

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_property))
        self.assertEqual("Manually geocoded (N/A)", refreshed_property.geocoding_confidence)

    def test_geocode_address_can_handle_receiving_no_buildings(self):
        self.assertIsNone(geocode_buildings(PropertyState.objects.none()))

    def test_geocoding_an_address_again_after_successful_geocode_executes_successfully(self):
        with base_vcr.use_cassette('seed/tests/data/vcr_cassettes/geocode_same_record_twice.yaml'):
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
            geocode_buildings(properties)

            refreshed_property = PropertyState.objects.get(pk=property.id)
            refreshed_property.address_line_1 = "2020 Lawrence St"
            refreshed_property.address_line_2 = "unit A"
            refreshed_property.postal_code = "80205"
            refreshed_property.save()

            refreshed_properties = PropertyState.objects.filter(pk=refreshed_property.id)
            geocode_buildings(refreshed_properties)

            refreshed_updated_property = PropertyState.objects.get(pk=refreshed_property.id)

            self.assertEqual('POINT (-104.991205 39.75251)', long_lat_wkt(refreshed_updated_property))
            self.assertEqual('High (P1AAA)', refreshed_updated_property.geocoding_confidence)
            self.assertEqual(-104.991205, refreshed_updated_property.longitude)
            self.assertEqual(39.75251, refreshed_updated_property.latitude)

    def test_geocoded_fields_are_changed_appropriately_if_a_user_manually_updates_latitude_or_longitude_of_ungeocoded_property(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property = PropertyState(**property_details)
        property.save()

        refreshed_property = PropertyState.objects.get(pk=property.id)
        self.assertIsNone(long_lat_wkt(refreshed_property))
        self.assertIsNone(refreshed_property.geocoding_confidence)

        refreshed_property.latitude = 39.765251
        refreshed_property.save()

        refreshed_property = PropertyState.objects.get(pk=property.id)
        self.assertEqual(39.765251, refreshed_property.latitude)
        self.assertIsNone(long_lat_wkt(refreshed_property))
        self.assertIsNone(refreshed_property.geocoding_confidence)

        refreshed_property.longitude = -104.986138
        refreshed_property.save()

        refreshed_property = PropertyState.objects.get(pk=property.id)
        self.assertEqual(-104.986138, refreshed_property.longitude)
        self.assertEqual('POINT (-104.986138 39.765251)', long_lat_wkt(refreshed_property))
        self.assertEqual("Manually geocoded (N/A)", refreshed_property.geocoding_confidence)

    def test_geocoded_fields_are_changed_appropriately_if_a_user_manually_updates_latitude_or_longitude_of_geocoded_property(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['latitude'] = 39.765251
        property_details['longitude'] = -104.986138
        property_details['long_lat'] = 'POINT (-104.986138 39.765251)'
        property_details['geocoding_confidence'] = 'High (P1AAA)'
        property = PropertyState(**property_details)
        property.save()

        # Make sure geocoding_confidence isn't overridden to be Manual given latitude and longitude are updated
        refreshed_property = PropertyState.objects.get(pk=property.id)
        self.assertEqual('High (P1AAA)', refreshed_property.geocoding_confidence)

        # Try updating latitude
        refreshed_property.latitude = 39.81
        refreshed_property.save()

        refreshed_property = PropertyState.objects.get(pk=property.id)
        self.assertEqual(39.81, refreshed_property.latitude)
        self.assertEqual('POINT (-104.986138 39.81)', long_lat_wkt(refreshed_property))
        self.assertEqual("Manually geocoded (N/A)", refreshed_property.geocoding_confidence)

        # If latitude or longitude are not there long_lat and geocoding_confidence should be empty
        refreshed_property.latitude = None
        refreshed_property.save()

        self.assertIsNone(refreshed_property.latitude)
        self.assertIsNone(long_lat_wkt(refreshed_property))
        self.assertIsNone(refreshed_property.geocoding_confidence)
