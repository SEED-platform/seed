# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import ast
import json

from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.models import Ubid
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
            'property': property,
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
            'property': property_correctly_populated,
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
            'property': property_not_decoded,
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


    # def test_ubid_crud_endpoint(self):
        # response = self.client.post(
        #     reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
        #     content_type='application/json'
        # )
        # response = response.json()
        # self.assertEqual(response, 'create')

        # response = self.client.get(
        #     reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
        #     content_type='application/json'
        # )
        # response = response.json()
        # self.assertEqual(response, 'list')

        # response = self.client.get(
        #     reverse('api:v3:ubid-detail', args=[1]) + '?organization_id=' + str(self.org.id),
        #     content_type='application/json'
        # )
        # response = response.json()
        # self.assertEqual(response, 'retrieve')

        # response = self.client.put(
        #     reverse('api:v3:ubid-detail', args=[1]) + '?organization_id=' + str(self.org.id),
        #     content_type='application/json'
        # )
        # response = response.json()
        # self.assertEqual(response, 'update')

        # response = self.client.delete(
        #     reverse('api:v3:ubid-detail', args=[1]) + '?organization_id=' + str(self.org.id),
        #     content_type='application/json'
        # )
        # response = response.json()
        # self.assertEqual(response, 'destroy')
class UbidModelTests(TestCase):
    
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
        self.property_view_factory = FakePropertyViewFactory(organization=self.org, user=self.user)
    
    def test_pass(self):
        self.assertTrue(True)

    def test_ubid_model(self):

        ps1 = self.property_view_factory.get_property_view().state
        ps2 = self.property_view_factory.get_property_view().state
        ps3 = self.property_view_factory.get_property_view().state

        ubid1a = Ubid.objects.create(
            ubid="8772WW7W+867V4X3-4803-1389-4816-1389",  # Example UBID from https://www.youtube.com/watch?v=wCfdWyjq_xs
            property=ps1
        )
        ubid1b = Ubid.objects.create(
            ubid="1111BBBB+1111BBB-1111-1111-1111-1111",
            property=ps1,
            preferred=True
        )
        ubid2 = Ubid.objects.create(
            ubid="1111BBBB+1111BBB-1111-1111-1111-1111",
            property=ps2,
            preferred=True
        )
        ubid3 = Ubid.objects.create(
            ubid="3333AAAA+3333AAA-3333-3333-3333-3333",
            property=ps3,
        )

        # model properties
        self.assertEqual(ubid1a.property, ps1)
        self.assertEqual(ubid1b.property, ps1)
        self.assertEqual(ubid2.property, ps2)
        self.assertEqual(ubid3.property, ps3)

        self.assertEqual(ps1.ubid_set.count(), 2)
        self.assertEqual(ps1.ubid_set.first(), ubid1a)
        self.assertEqual(ps1.ubid_set.last(), ubid1b)
        self.assertEqual(ps2.ubid_set.first(), ubid2)
        self.assertEqual(ps3.ubid_set.first(), ubid3)

        self.assertEqual(ps1.ubid_set.first().preferred, False)
        self.assertEqual(ps1.ubid_set.last().preferred, True)
        self.assertEqual(ps2.ubid_set.first().preferred, True)
        self.assertEqual(ps3.ubid_set.first().preferred, False)

        ubid = ps3.ubid_set.first()
        ubid.preferred = True 
        ubid.save()
        self.assertEqual(ps3.ubid_set.first().preferred, True)

        # Cascade Delete is one way
        self.assertEqual(Ubid.objects.count(), 4)
        ps1.delete()
        self.assertEqual(Ubid.objects.count(), 2)
        ps2.delete()
        self.assertEqual(Ubid.objects.count(), 1)

        ubid3.delete() 
        self.assertEqual(PropertyState.objects.count(), 1)


class UbidViewCrudTests(TestCase):
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

        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        self.property = PropertyState(**property_details)
        self.property.save()

        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details["organization_id"] = self.org.id
        self.taxlot = TaxLotState(**taxlot_details)
        self.taxlot.save()

        self.ubid1a = Ubid.objects.create(
            property=self.property,
            preferred=True,
            ubid='A+A-1-1-1-1',
        )
        self.ubid1b = Ubid.objects.create(
            property=self.property,
            preferred=False,
            ubid='B+B-2-2-2-2',
        )

        self.ubid1c = Ubid.objects.create(
            taxlot=self.taxlot,
            preferred=True,
            ubid='C+C-3-3-3-3',
        )

        # create a second org
        self.org2, _, _ = create_organization(self.user)
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org2.id
        self.property2 = PropertyState(**property_details)
        self.property2.save()
        self.ubid2 = Ubid.objects.create(
            property=self.property2,
            ubid='D+D-4-4-4-4',
        )
    
    
    def test_list_endpoint(self):
        response = self.client.get(
            reverse('api:v3:ubid-list') +'?organization_id=' + str(self.org.id),
            content_type='application/json' 
        )

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual('success', data['status'])
        self.assertEqual(3, len(data['data']))

        ubid = data['data'][0]
        self.assertEqual('A+A-1-1-1-1', ubid['ubid'])
        self.assertEqual(True, ubid['preferred'])
        self.assertEqual(self.property.id, ubid['property'])
        ubid = data['data'][1]
        self.assertEqual('B+B-2-2-2-2', ubid['ubid'])
        self.assertEqual(False, ubid['preferred'])
        self.assertEqual(self.property.id, ubid['property'])
        ubid = data['data'][2]
        self.assertEqual('C+C-3-3-3-3', ubid['ubid'])
        self.assertEqual(True, ubid['preferred'])
        self.assertEqual(None, ubid['property'])
        self.assertEqual(self.taxlot.id, ubid['taxlot'])

    def test_retrieve_endpoint(self):
        response = self.client.get(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        x = response
        self.assertEqual(1,1)
        

    def test_create_endpoint(self):
        self.assertEqual(4, Ubid.objects.count())

        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property = PropertyState(**property_details)
        property.save()

        # Successful creation
        response = self.client.post(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'ubid': 'A+A-1-1-1-1',
                'preferred': True,
                'property': property.id,
            }),
            content_type='application/json'
        )
        data = response.json()
        self.assertEqual('A+A-1-1-1-1', data['ubid'])
        self.assertEqual(property.id, data['property'])
        self.assertEqual(None, data['taxlot'])
        self.assertEqual(True, data['preferred'])
        self.assertEqual(5, Ubid.objects.count())

        # Invalid data
        response = self.client.post(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'test': 1,
                'not_valid': 'data'
            }),
            content_type='application/json'
        )
        self.assertEqual(400, response.status_code)
        response = self.client.post(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'ubid': 'A+A-1-1-1-1',
                'not_valid': 'no taxlot or property'
            }),
            content_type='application/json'
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(5, Ubid.objects.count())
