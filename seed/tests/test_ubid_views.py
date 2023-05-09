# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import ast

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.models.ubids import Ubid
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory
)
from seed.utils.geocode import bounding_box_wkt, wkt_to_polygon
from seed.utils.organizations import create_organization
from seed.utils.ubid import centroid_wkt


class UbidViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.taxlot_state_factory = FakeTaxLotStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.taxlot_view_factory = FakeTaxLotViewFactory(organization=self.org)

    def test_ubid_decode_by_id_endpoint_base(self):
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        # property_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'

        property = PropertyState(**property_details)
        property.save()

        ubid_details = {
            'ubid': '86HJPCWQ+2VV-1-3-2-3',
            'preferred': True,
            'property': property
        }

        ubid = Ubid(**ubid_details)
        ubid.save()

        property_view = self.property_view_factory.get_property_view(state=property)

        url = reverse('api:v3:ubid-decode-by-ids') + '?organization_id=%s' % self.org.pk
        post_params = {'property_view_ids': [property_view.id]}

        self.client.post(url, post_params)

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

    def test_decode_ubid_results_returns_a_summary_dictionary(self):
        property_none_details = self.property_state_factory.get_details()
        property_none_details["organization_id"] = self.org.id
        property_none = PropertyState(**property_none_details)
        property_none.save()

        property_none_view = self.property_view_factory.get_property_view(state=property_none)

        property_correctly_populated_details = self.property_state_factory.get_details()
        property_correctly_populated_details["organization_id"] = self.org.id
        property_correctly_populated_details['bounding_box'] = (
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )
        property_correctly_populated_details['centroid'] = (
            "POLYGON ((-87.56031249999999 41.74509999999998, "
            "-87.56031249999999 41.74512499999997, "
            "-87.56034374999999 41.74512499999997, "
            "-87.56034374999999 41.74509999999998, "
            "-87.56031249999999 41.74509999999998))"
        )
        property_correctly_populated = PropertyState(**property_correctly_populated_details)
        property_correctly_populated.save()

        ubid_details = {
            'ubid': '86HJPCWQ+2VV-1-3-2-3',
            'preferred': True,
            'property': property_correctly_populated
        }
        ubid = Ubid(**ubid_details)
        ubid.save()

        property_correctly_populated_view = self.property_view_factory.get_property_view(state=property_correctly_populated)

        property_not_decoded_details = self.property_state_factory.get_details()
        property_not_decoded_details["organization_id"] = self.org.id
        # bounding_box could be populated from a GeoJSON import
        property_not_decoded_details['bounding_box'] = (
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )
        property_not_decoded = PropertyState(**property_not_decoded_details)
        property_not_decoded.save()

        ubid_details = {
            'ubid': '86HJPCWQ+2VV-1-3-2-3',
            'preferred': True,
            'property': property_not_decoded
        }
        ubid = Ubid(**ubid_details)
        ubid.save()

        property_not_decoded_view = self.property_view_factory.get_property_view(state=property_not_decoded)

        url = reverse('api:v3:ubid-decode-results') + '?organization_id=%s' % self.org.pk
        post_params = {
            'property_view_ids': [
                property_none_view.id,
                property_correctly_populated_view.id,
                property_not_decoded_view.id
            ]
        }

        result = self.client.post(url, post_params)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "ubid_unpopulated": 1,
            "ubid_successfully_decoded": 1,
            "ubid_not_decoded": 1,
            "ulid_unpopulated": 0,
            "ulid_successfully_decoded": 0,
            "ulid_not_decoded": 0
        }

        self.assertEqual(result_dict, expectation)

    def test_decode_ulid_results_returns_a_summary_dictionary(self):
        taxlot_none_details = self.taxlot_state_factory.get_details()
        taxlot_none_details["organization_id"] = self.org.id
        taxlot_none = TaxLotState(**taxlot_none_details)
        taxlot_none.save()

        taxlot_none_view = self.taxlot_view_factory.get_taxlot_view(state=taxlot_none)

        taxlot_correctly_populated_details = self.taxlot_state_factory.get_details()
        taxlot_correctly_populated_details["organization_id"] = self.org.id
        taxlot_correctly_populated_details['ulid'] = '86HJPCWQ+2VV-1-3-2-3'
        taxlot_correctly_populated_details['bounding_box'] = (
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )
        taxlot_correctly_populated_details['centroid'] = (
            "POLYGON ((-87.56031249999999 41.74509999999998, "
            "-87.56031249999999 41.74512499999997, "
            "-87.56034374999999 41.74512499999997, "
            "-87.56034374999999 41.74509999999998, "
            "-87.56031249999999 41.74509999999998))"
        )
        taxlot_correctly_populated = TaxLotState(**taxlot_correctly_populated_details)
        taxlot_correctly_populated.save()

        taxlot_correctly_populated_view = self.taxlot_view_factory.get_taxlot_view(state=taxlot_correctly_populated)

        taxlot_not_decoded_details = self.taxlot_state_factory.get_details()
        taxlot_not_decoded_details["organization_id"] = self.org.id
        taxlot_not_decoded_details['ulid'] = '86HJPCWQ+2VV-1-3-2-3'
        # bounding_box could be populated from a GeoJSON import
        taxlot_not_decoded_details['bounding_box'] = (
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )
        taxlot_not_decoded = TaxLotState(**taxlot_not_decoded_details)
        taxlot_not_decoded.save()

        taxlot_not_decoded_view = self.taxlot_view_factory.get_taxlot_view(state=taxlot_not_decoded)

        url = reverse('api:v3:ubid-decode-results') + '?organization_id=%s' % self.org.pk
        post_params = {
            'taxlot_view_ids': [
                taxlot_none_view.id,
                taxlot_correctly_populated_view.id,
                taxlot_not_decoded_view.id
            ]
        }

        result = self.client.post(url, post_params)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            "ubid_unpopulated": 0,
            "ubid_successfully_decoded": 0,
            "ubid_not_decoded": 0,
            "ulid_unpopulated": 1,
            "ulid_successfully_decoded": 1,
            "ulid_not_decoded": 1
        }

        self.assertEqual(result_dict, expectation)


    def test_ubid_crud_endpoint(self):
        response = self.client.post(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        response = response.json()
        self.assertEqual(response, 'create')

        response = self.client.get(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        response = response.json()
        self.assertEqual(response, 'list')

        response = self.client.get(
            reverse('api:v3:ubid-detail', args=[1]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        response = response.json()
        self.assertEqual(response, 'retrieve')

        response = self.client.put(
            reverse('api:v3:ubid-detail', args=[1]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        response = response.json()
        self.assertEqual(response, 'update')

        response = self.client.delete(
            reverse('api:v3:ubid-detail', args=[1]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        response = response.json()
        self.assertEqual(response, 'destroy')


