# !/usr/bin/env python
# encoding: utf-8

import ast
import copy
import json

from django.urls import reverse

from seed.data_importer.utils import \
    kbtu_thermal_conversion_factors as conversion_factors
from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import (
    FakePropertyViewFactory
)
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization


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
        url = reverse('api:v3:properties-valid-meter-types-and-units')

        result = self.client.get(url)
        result_dict = ast.literal_eval(result.content.decode("utf-8"))

        expectation = {
            type: list(units.keys()) for type, units in conversion_factors("US").items()
        }

        self.assertEqual(result_dict, expectation)


class TestMeterCRUD(DataMappingBaseTestCase):
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

        # faker class for properties
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

    def test_create_meter(self):
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})

        payload = {
            'property_id': property_view.property.id,
            'type': 'Electric - Grid',
            'source': 'GreenButton',
            'source_id': '1234567890',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

        payload = {
            'property_id': property_view.property.id,
            'type': 'Electric - Grid',
            'source': 'GreenButton',
            'source_id': '/v1/User/000/UsagePoint/123fakeID/MeterReading/000',
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        # verify that the source_id gets updated when GreenButton
        self.assertEqual(response.data['source_id'], '123fakeID')

        payload = {
            'property_id': property_view.property.id,
            'type': 'Natural Gas',
            'source': 'Portfolio Manager',
            'source_id': 'A Custom Source ID',
            'is_virtual': True,
        }

        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

    def test_delete_meter(self):
        # create meter
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})
        payload = {
            'property_id': property_view.property.id,
            'type': 'Natural Gas',
            'source': 'Portfolio Manager',
            'source_id': 'A Custom Source ID',
            'is_virtual': True,
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

        # verify that there is only 1 meter for property
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        meter_id = response.data[0]['id']
        meter_url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': property_view.id, 'pk': meter_id})
        response = self.client.delete(meter_url, content_type='application/json')
        self.assertEqual(response.status_code, 204)
        # make sure there are no meters for property
        response = self.client.get(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_update_meter(self):
        # create meter
        property_view = self.property_view_factory.get_property_view()
        url = reverse('api:v3:property-meters-list', kwargs={'property_pk': property_view.id})
        payload = {
            'property_id': property_view.property.id,
            'type': 'Natural Gas',
            'source': 'Portfolio Manager',
            'source_id': 'A Custom Source ID',
            'is_virtual': False,
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertDictContainsSubset(payload, response.data)

        new_payload = copy.deepcopy(payload)
        new_payload['is_virtual'] = True
        meter_id = response.data['id']
        meter_url = reverse('api:v3:property-meters-detail', kwargs={'property_pk': property_view.id, 'pk': meter_id})
        response = self.client.put(meter_url, data=json.dumps(new_payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['is_virtual'], True)
