# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.contrib.gis.geos import Polygon
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakeTaxLotStateFactory
)
from seed.utils.geocode import bounding_box_wkt, wkt_to_polygon
from seed.utils.organizations import create_organization
from seed.utils.ubid import centroid_wkt, decode_unique_ids


class UbidSpecificWktMethods(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.org.save()

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)

    def test_centroid_wkt_takes_a_state_and_returns_the_WKT_string_or_None(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

        no_centroid_property = PropertyState(**property_details)
        no_centroid_property.save()

        property_details['centroid'] = 'POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))'

        centroid_property = PropertyState(**property_details)
        centroid_property.save()

        no_centroid_record = PropertyState.objects.get(pk=no_centroid_property.id)
        geocoded_record = PropertyState.objects.get(pk=centroid_property.id)

        self.assertIsNone(no_centroid_record.centroid)
        self.assertIsNone(centroid_wkt(no_centroid_record))

        self.assertIsInstance(geocoded_record.centroid, Polygon)
        self.assertEqual('POLYGON ((0 0, 4 0, 4 4, 0 4, 0 0))', centroid_wkt(centroid_property))


class UbidUtilMethods(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.org.save()

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)

    def test_decode_ubids_is_successful_when_valid_UBID_provided(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'

        property = PropertyState(**property_details)
        property.save()
        properties = PropertyState.objects.filter(pk=property.id)

        decode_unique_ids(properties)
        refreshed_property = PropertyState.objects.get(pk=property.id)
        known_property_bounding_box = wkt_to_polygon(
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )['coordinates'][0]

        known_property_centroid = wkt_to_polygon(
            "POLYGON ((-87.5603125 41.74509999999998, "
            "-87.5603125 41.74512499999997, "
            "-87.56034374999999 41.74512499999997, "
            "-87.56034374999999 41.74509999999998, "
            "-87.5603125 41.74509999999998))"
        )['coordinates'][0]

        # Need to check that these are almost equal. Underlying gdal methods
        # vary slightly on linux vs mac
        for index, coord in enumerate(wkt_to_polygon(bounding_box_wkt(refreshed_property))['coordinates'][0]):
            self.assertAlmostEqual(coord[0], known_property_bounding_box[index][0])
            self.assertAlmostEqual(coord[1], known_property_bounding_box[index][1])

        for index, coord in enumerate(wkt_to_polygon(centroid_wkt(refreshed_property))['coordinates'][0]):
            self.assertAlmostEqual(coord[0], known_property_centroid[index][0])
            self.assertAlmostEqual(coord[1], known_property_centroid[index][1])

        self.assertAlmostEqual(refreshed_property.latitude, 41.7451)
        self.assertAlmostEqual(refreshed_property.longitude, -87.560328125)

    def test_decode_taxlot_ubids_is_successful_when_valid_taxlot_UBID_provided(self):
        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details['organization_id'] = self.org.id
        taxlot_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'

        taxlot = TaxLotState(**taxlot_details)
        taxlot.save()
        taxlots = TaxLotState.objects.filter(pk=taxlot.id)

        decode_unique_ids(taxlots)
        refreshed_taxlot = TaxLotState.objects.get(pk=taxlot.id)

        known_taxlot_bounding_box = wkt_to_polygon(
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )['coordinates'][0]

        known_taxlot_centroid = wkt_to_polygon(
            "POLYGON ((-87.5603125 41.74509999999998, "
            "-87.5603125 41.74512499999997, "
            "-87.56034374999999 41.74512499999997, "
            "-87.56034374999999 41.74509999999998, "
            "-87.5603125 41.74509999999998))"
        )['coordinates'][0]

        # Need to check that these are almost equal. Underlying gdal methods
        # vary slightly on linux vs mac
        for index, coord in enumerate(wkt_to_polygon(bounding_box_wkt(refreshed_taxlot))['coordinates'][0]):
            self.assertAlmostEqual(coord[0], known_taxlot_bounding_box[index][0])
            self.assertAlmostEqual(coord[1], known_taxlot_bounding_box[index][1])

        for index, coord in enumerate(wkt_to_polygon(centroid_wkt(refreshed_taxlot))['coordinates'][0]):
            self.assertAlmostEqual(coord[0], known_taxlot_centroid[index][0])
            self.assertAlmostEqual(coord[1], known_taxlot_centroid[index][1])

        self.assertAlmostEqual(refreshed_taxlot.latitude, 41.7451)
        self.assertAlmostEqual(refreshed_taxlot.longitude, -87.560328125)

    def test_decode_ubids_does_nothing_if_no_UBID_provided(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id

        property = PropertyState(**property_details)
        property.save()
        properties = PropertyState.objects.filter(pk=property.id)

        decode_unique_ids(properties)
        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertIsNone(bounding_box_wkt(refreshed_property))
        self.assertIsNone(centroid_wkt(refreshed_property))

    def test_decode_taxlot_ubids_does_nothing_if_no_taxlot_UBID_provided(self):
        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details['organization_id'] = self.org.id

        taxlot = TaxLotState(**taxlot_details)
        taxlot.save()
        taxlots = PropertyState.objects.filter(pk=taxlot.id)

        decode_unique_ids(taxlots)
        refreshed_taxlot = TaxLotState.objects.get(pk=taxlot.id)

        self.assertIsNone(bounding_box_wkt(refreshed_taxlot))
        self.assertIsNone(centroid_wkt(refreshed_taxlot))

    def test_decode_ubids_doesnt_throw_an_error_if_an_invalid_ubid_is_provided(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['ubid'] = 'invalidubid'

        property = PropertyState(**property_details)
        property.save()
        properties = PropertyState.objects.filter(pk=property.id)

        decode_unique_ids(properties)

        refreshed_property = PropertyState.objects.get(pk=property.id)

        self.assertIsNone(bounding_box_wkt(refreshed_property))
        self.assertIsNone(centroid_wkt(refreshed_property))

    def test_decode_taxlot_ubids_doesnt_throw_an_error_if_an_invalid_ubid_is_provided(self):
        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details['organization_id'] = self.org.id
        taxlot_details['ubid'] = 'invalidubid'

        taxlot = TaxLotState(**taxlot_details)
        taxlot.save()
        taxlots = TaxLotState.objects.filter(pk=taxlot.id)

        decode_unique_ids(taxlots)

        refreshed_taxlot = TaxLotState.objects.get(pk=taxlot.id)

        self.assertIsNone(bounding_box_wkt(refreshed_taxlot))
        self.assertIsNone(centroid_wkt(refreshed_taxlot))
