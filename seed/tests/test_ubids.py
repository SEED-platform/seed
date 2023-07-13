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
from seed.models import UbidModel
from seed.models.properties import PropertyState
from seed.models.tax_lots import TaxLotState
from seed.test_helpers.fake import (
    FakePropertyStateFactory,
    FakePropertyViewFactory,
    FakeTaxLotStateFactory,
    FakeTaxLotViewFactory
)
from seed.utils.geocode import bounding_box_wkt, wkt_to_polygon
from seed.utils.organizations import create_organization
from seed.utils.ubid import centroid_wkt, get_jaccard_index, validate_ubid


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
        property_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'

        property = PropertyState(**property_details)
        property.save()

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

    def test_decode_property_ubid_results_returns_a_summary_dictionary(self):
        property_none_details = self.property_state_factory.get_details()
        property_none_details["organization_id"] = self.org.id
        property_none = PropertyState(**property_none_details)
        property_none.save()

        property_none_view = self.property_view_factory.get_property_view(state=property_none)

        property_correctly_populated_details = self.property_state_factory.get_details()
        property_correctly_populated_details["organization_id"] = self.org.id
        property_correctly_populated_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
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

        property_correctly_populated_view = self.property_view_factory.get_property_view(state=property_correctly_populated)

        property_not_decoded_details = self.property_state_factory.get_details()
        property_not_decoded_details["organization_id"] = self.org.id
        property_not_decoded_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
        # bounding_box could be populated from a GeoJSON import
        property_not_decoded_details['bounding_box'] = (
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )
        property_not_decoded = PropertyState(**property_not_decoded_details)
        # When the property is saved with a UBID that is not in the UBID table it will be automatically decoded
        property_not_decoded.save()

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
            "ubid_successfully_decoded": 2,
            "ubid_not_decoded": 0,
        }

        self.assertEqual(result_dict, expectation)

    def test_decode_taxlot_ubid_results_returns_a_summary_dictionary(self):
        taxlot_none_details = self.taxlot_state_factory.get_details()
        taxlot_none_details["organization_id"] = self.org.id
        taxlot_none = TaxLotState(**taxlot_none_details)
        taxlot_none.save()

        taxlot_none_view = self.taxlot_view_factory.get_taxlot_view(state=taxlot_none)

        taxlot_correctly_populated_details = self.taxlot_state_factory.get_details()
        taxlot_correctly_populated_details["organization_id"] = self.org.id
        taxlot_correctly_populated_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
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
        taxlot_not_decoded_details['ubid'] = '86HJPCWQ+2VV-1-3-2-3'
        # bounding_box could be populated from a GeoJSON import
        taxlot_not_decoded_details['bounding_box'] = (
            "POLYGON ((-87.56021875000002 41.74504999999999, "
            "-87.56021875000002 41.74514999999997, "
            "-87.56043749999996 41.74514999999997, "
            "-87.56043749999996 41.74504999999999, "
            "-87.56021875000002 41.74504999999999))"
        )
        taxlot_not_decoded = TaxLotState(**taxlot_not_decoded_details)
        # When the taxlot is saved with a UBID that is not in the UBID table it will be automatically decoded
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
            "ubid_unpopulated": 1,
            "ubid_successfully_decoded": 2,
            "ubid_not_decoded": 0,
        }

        self.assertEqual(result_dict, expectation)


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

        ubid1a = UbidModel.objects.create(
            ubid="8772WW7W+867V4X3-4803-1389-4816-1389",  # Example UBID from https://www.youtube.com/watch?v=wCfdWyjq_xs
            property=ps1
        )
        ubid1b = UbidModel.objects.create(
            ubid="1111BBBB+1111BBB-1111-1111-1111-1111",
            property=ps1,
            preferred=True
        )
        ubid2 = UbidModel.objects.create(
            ubid="1111BBBB+1111BBB-1111-1111-1111-1111",
            property=ps2,
            preferred=True
        )
        ubid3 = UbidModel.objects.create(
            ubid="3333AAAA+3333AAA-3333-3333-3333-3333",
            property=ps3,
        )

        # model properties
        self.assertEqual(ubid1a.property, ps1)
        self.assertEqual(ubid1b.property, ps1)
        self.assertEqual(ubid2.property, ps2)
        self.assertEqual(ubid3.property, ps3)

        self.assertEqual(ps1.ubidmodel_set.count(), 2)
        self.assertEqual(ps1.ubidmodel_set.first(), ubid1a)
        self.assertEqual(ps1.ubidmodel_set.last(), ubid1b)
        self.assertEqual(ps2.ubidmodel_set.first(), ubid2)
        self.assertEqual(ps3.ubidmodel_set.first(), ubid3)

        self.assertEqual(ps1.ubidmodel_set.first().preferred, False)
        self.assertEqual(ps1.ubidmodel_set.last().preferred, True)
        self.assertEqual(ps2.ubidmodel_set.first().preferred, True)
        self.assertEqual(ps3.ubidmodel_set.first().preferred, False)

        ubid = ps3.ubidmodel_set.first()
        ubid.preferred = True
        ubid.save()
        self.assertEqual(ps3.ubidmodel_set.first().preferred, True)

        # Cascade Delete is one way
        self.assertEqual(UbidModel.objects.count(), 4)
        ps1.delete()
        self.assertEqual(UbidModel.objects.count(), 2)
        ps2.delete()
        self.assertEqual(UbidModel.objects.count(), 1)

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

        self.ubid1a = UbidModel.objects.create(
            property=self.property,
            preferred=True,
            ubid='A+A-1-1-1-1',
        )
        self.ubid1b = UbidModel.objects.create(
            property=self.property,
            preferred=False,
            ubid='B+B-2-2-2-2',
        )

        self.ubid1c = UbidModel.objects.create(
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
        self.ubid2 = UbidModel.objects.create(
            property=self.property2,
            ubid='D+D-4-4-4-4',
        )

    def test_list_endpoint(self):
        response = self.client.get(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
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
        # Retrieve property ubid
        response = self.client.get(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual('success', data['status'])
        self.assertEqual('A+A-1-1-1-1', data['data']['ubid'])
        self.assertEqual(True, data['data']['preferred'])
        self.assertEqual(self.property.id, data['data']['property'])
        self.assertEqual(None, data['data']['taxlot'])

        # retrieve taxlot ubid
        response = self.client.get(
            reverse('api:v3:ubid-detail', args=[self.ubid1c.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual('success', data['status'])
        self.assertEqual('C+C-3-3-3-3', data['data']['ubid'])
        self.assertEqual(True, data['data']['preferred'])
        self.assertEqual(None, data['data']['property'])
        self.assertEqual(self.taxlot.id, data['data']['taxlot'])

        # invalid id
        response = self.client.get(
            reverse('api:v3:ubid-detail', args=[-1]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )

        self.assertEqual(404, response.status_code)
        data = response.json()
        self.assertEqual('error', data['status'])
        self.assertEqual('UBID with id -1 does not exist', data['message'])

    def test_create_endpoint(self):
        self.assertEqual(4, UbidModel.objects.count())

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
        ubid1 = property.ubidmodel_set.first()
        self.assertEqual(201, response.status_code)
        self.assertEqual('success', response.json()['status'])
        data = response.json()['data']
        self.assertEqual('A+A-1-1-1-1', data['ubid'])
        self.assertEqual(property.id, data['property'])
        self.assertEqual(None, data['taxlot'])
        self.assertEqual(True, data['preferred'])
        self.assertEqual(5, UbidModel.objects.count())

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
        self.assertEqual(5, UbidModel.objects.count())

        # 2 Preferred Ubids
        response = self.client.post(
            reverse('api:v3:ubid-list') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'ubid': 'B+B-1-1-1-1',
                'preferred': True,
                'property': property.id,
            }),
            content_type='application/json'
        )

        self.assertEqual(ubid1.id, property.ubidmodel_set.first().id)
        ubid1 = property.ubidmodel_set.first()
        ubid2 = property.ubidmodel_set.last()
        self.assertFalse(ubid1 == ubid2)
        self.assertFalse(ubid1.preferred)
        self.assertTrue(ubid2.preferred)

    def test_update_endpoint(self):
        # Valid Data
        self.assertEqual('A+A-1-1-1-1', self.ubid1a.ubid)
        response = self.client.put(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'ubid': 'Z+Z-1-1-1-1'
            }),
            content_type='application/json'
        )

        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual('success', data['status'])
        self.assertEqual(self.ubid1a.id, data['data']['id'])
        self.assertEqual('Z+Z-1-1-1-1', data['data']['ubid'])
        self.assertEqual(True, data['data']['preferred'])
        self.assertEqual(self.property.id, data['data']['property'])
        self.assertEqual(None, data['data']['taxlot'])

        response = self.client.put(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'preferred': False
            }),
            content_type='application/json'
        )
        self.assertEqual(200, response.status_code)
        data = response.json()
        self.assertEqual('Z+Z-1-1-1-1', data['data']['ubid'])
        self.assertEqual(False, data['data']['preferred'])

        # Invalid Data
        response = self.client.put(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'invalid': 'data'
            }),
            content_type='application/json'
        )
        self.assertEqual(422, response.status_code)
        data = response.json()
        self.assertEqual('error', data['status'])
        self.assertEqual("Invalid field 'invalid' given. Accepted fields are ['ubid', 'preferred']", data['message'])

    def test_destroy_endpoint(self):
        # Valid id
        self.assertEqual(4, UbidModel.objects.count())
        self.assertTrue(self.ubid1a in UbidModel.objects.all())
        response = self.client.delete(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        self.assertEqual(204, response.status_code)
        self.assertEqual(3, UbidModel.objects.count())
        self.assertTrue(self.ubid1a not in UbidModel.objects.all())

        # Invalid id
        response = self.client.delete(
            reverse('api:v3:ubid-detail', args=[self.ubid1a.id]) + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        self.assertEqual(404, response.status_code)
        self.assertEqual('Not found.', response.json()['detail'])

    def test_get_ubids_by_view(self):
        property_view = self.property_view_factory.get_property_view(state=self.property)
        property_view2 = self.property_view_factory.get_property_view()

        response = self.client.post(
            reverse('api:v3:ubid-ubids-by-view') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'view_id': property_view.id,
                'type': 'property'
            }),
            content_type='application/json'
        )

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual('success', body['status'])

        data = body['data']
        self.assertEqual(2, len(data))
        self.assertEqual(data[0]['id'], self.ubid1a.id)
        self.assertEqual(data[0]['ubid'], self.ubid1a.ubid)
        self.assertEqual(data[0]['preferred'], self.ubid1a.preferred)
        self.assertEqual(data[0]['property'], self.ubid1a.property.id)
        self.assertEqual(data[0]['taxlot'], self.ubid1a.taxlot)
        self.assertEqual(data[1]['id'], self.ubid1b.id)
        self.assertEqual(data[1]['ubid'], self.ubid1b.ubid)
        self.assertEqual(data[1]['preferred'], self.ubid1b.preferred)
        self.assertEqual(data[1]['property'], self.ubid1b.property.id)
        self.assertEqual(data[1]['taxlot'], self.ubid1b.taxlot)

        # invalid - missing data
        response = self.client.post(
            reverse('api:v3:ubid-ubids-by-view') + '?organization_id=' + str(self.org.id),
            content_type='application/json'
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual('error', response.json()['status'])
        self.assertEqual('view_id and type (property or taxlot) are required', response.json()['message'])

        # invalid view id
        response = self.client.post(
            reverse('api:v3:ubid-ubids-by-view') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'view_id': -1,
                'type': 'property'
            }),
            content_type='application/json'
        )
        self.assertEqual(404, response.status_code)
        self.assertEqual('error', response.json()['status'])
        self.assertEqual('View with id -1 does not exist', response.json()['message'])

        # invalid type
        response = self.client.post(
            reverse('api:v3:ubid-ubids-by-view') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'view_id': property_view.id,
                'type': 'INVALID'
            }),
            content_type='application/json'
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual('error', response.json()['status'])
        self.assertEqual('view_id and type (property or taxlot) are required', response.json()['message'])

        # property state has no ubids
        response = self.client.post(
            reverse('api:v3:ubid-ubids-by-view') + '?organization_id=' + str(self.org.id),
            data=json.dumps({
                'view_id': property_view2.id,
                'type': 'property'
            }),
            content_type='application/json'
        )

        self.assertEqual(200, response.status_code)
        self.assertEqual('success', response.json()['status'])
        self.assertEqual([], response.json()['data'])


class UbidModelSignalCreationTests(TestCase):
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

    def test_create_ubid_from_property_state_signal(self):
        self.assertEqual(0, UbidModel.objects.count())
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['ubid'] = 'A+A-1-1-1-1'
        property1 = PropertyState(**property_details)
        property1.save()
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['ubid'] = 'B+B-1-1-1-1'
        property2 = PropertyState(**property_details)
        property2.save()
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property_details['ubid'] = 'C+C-1-1-1-1'
        property3 = PropertyState(**property_details)
        property3.save()
        property_details = self.property_state_factory.get_details()
        property_details['organization_id'] = self.org.id
        property4 = PropertyState(**property_details)
        property4.save()

        self.assertEqual(3, UbidModel.objects.count())

        # avoid duplicate ubid models
        property1.ubid = 'A+A-1-1-1-1'
        property1.save()
        self.assertEqual(3, UbidModel.objects.count())

        property1.ubid = 'X+X-1-1-1-1'
        property1.save()
        self.assertEqual(4, UbidModel.objects.count())
        self.assertEqual(2, property1.ubidmodel_set.count())
        ubidx = UbidModel.objects.get(ubid='X+X-1-1-1-1')
        self.assertTrue(ubidx.preferred)
        self.assertEqual(property1, ubidx.property)
        self.assertEqual(None, ubidx.taxlot)

        property4.ubid = 'D+D-1-1-1-1'
        property4.save()
        self.assertEqual(5, UbidModel.objects.count())

    def test_create_ubid_from_taxlot_state_signal(self):
        self.assertEqual(0, UbidModel.objects.count())
        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details['organization_id'] = self.org.id
        taxlot_details['ubid'] = 'E+E-1-1-1-1'
        taxlot1 = TaxLotState(**taxlot_details)
        taxlot1.save()
        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details['organization_id'] = self.org.id
        taxlot_details['ubid'] = 'F+F-1-1-1-1'
        taxlot2 = TaxLotState(**taxlot_details)
        taxlot2.save()
        taxlot_details = self.taxlot_state_factory.get_details()
        taxlot_details['organization_id'] = self.org.id
        taxlot3 = TaxLotState(**taxlot_details)
        taxlot3.save()

        self.assertEqual(2, UbidModel.objects.count())

        # avoid duplicate ubid models
        taxlot1.ubid = 'E+E-1-1-1-1'
        taxlot1.save()
        self.assertEqual(2, UbidModel.objects.count())

        taxlot1.ubid = 'Y+Y-1-1-1-1'
        taxlot1.save()
        self.assertEqual(3, UbidModel.objects.count())
        self.assertEqual(2, taxlot1.ubidmodel_set.count())
        ubidy = UbidModel.objects.get(ubid='Y+Y-1-1-1-1')
        self.assertTrue(ubidy.preferred)
        self.assertEqual(taxlot1, ubidy.taxlot)
        self.assertEqual(None, ubidy.property)

        taxlot3.ubid = 'D+D-1-1-1-1'
        taxlot3.save()
        self.assertEqual(4, UbidModel.objects.count())


class UbidSqlTests(TestCase):

    def test_jaccard(self):
        # nrel cafe
        ubid_cafe = '85FPPRR9+3C-0-0-0-0'
        ubid_cafe_larger = '85FPPRR9+3C-1-1-1-1'
        ubid_cafe_north = '85FPPRR9+4C-0-0-1-0'

        # nrel FTLB
        ubid_ftlb = '85FPPRR9+38-0-0-0-0'
        ubid_ftlb_west = '85FPPRR9+38-0-0-0-2'
        ubid_ftlb_south = '85FPPRR9+28-1-0-0-1'

        # exact
        jaccard = get_jaccard_index(ubid_cafe, ubid_cafe)
        self.assertEqual(1.0, float(jaccard))
        jaccard = get_jaccard_index(ubid_ftlb, ubid_ftlb)
        self.assertEqual(1.0, float(jaccard))

        # partial
        jaccard = get_jaccard_index(ubid_cafe, ubid_cafe_larger)
        self.assertEqual((1 / 9), float(jaccard))
        jaccard = get_jaccard_index(ubid_cafe, ubid_cafe_north)
        self.assertEqual(0.5, float(jaccard))

        jaccard = get_jaccard_index(ubid_ftlb, ubid_ftlb_west)
        self.assertEqual((1 / 3), float(jaccard))
        jaccard = get_jaccard_index(ubid_ftlb, ubid_ftlb_south)
        self.assertEqual(0.25, float(jaccard))

        # different
        jaccard = get_jaccard_index(ubid_cafe, ubid_ftlb)
        self.assertEqual(0, float(jaccard))

        # invalid ubid
        invalid = 'invalid'
        validity = validate_ubid(invalid)
        self.assertFalse(validity)
        validity = validate_ubid(ubid_cafe)
        self.assertTrue(validity)

        jaccard = get_jaccard_index(ubid_cafe, invalid)
        self.assertEqual(0, float(jaccard))
        jaccard = get_jaccard_index(invalid, invalid)
        self.assertEqual(1.0, float(jaccard))
