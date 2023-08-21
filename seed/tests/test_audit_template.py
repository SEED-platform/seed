# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

import mock
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from seed.utils.organizations import create_organization


class AuditTemplateViewTests(TestCase):
    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.org.at_organization_token = "fake at_api_token"
        self.org.audit_template_user = "fake at user"
        self.org.audit_template_password = "fake at password"
        self.org.save()

        self.client.login(**self.user_details)

        self.get_building_url = reverse('api:v3:audit_template-get-building-xml', args=['1'])
        self.get_buildings_url = reverse('api:v3:audit_template-get-buildings')

        self.good_authenticate_response = mock.Mock()
        self.good_authenticate_response.status_code = 200
        self.good_authenticate_response.json = mock.Mock(return_value={"token": "fake token"})

        self.bad_authenticate_response = mock.Mock()
        self.bad_authenticate_response.status_code = 400
        self.bad_authenticate_response.content = {"error": "Invalid email, password or organization_token."}

        self.good_get_building_response = mock.Mock()
        self.good_get_building_response.status_code = 200
        self.good_get_building_response.text = "building response"

        self.bad_get_building_response = mock.Mock()
        self.bad_get_building_response.status_code = 400
        self.bad_get_building_response.content = "bad building response"

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.good_authenticate_response, self.good_get_building_response]
        response = self.client.get(self.get_building_url, data={"organization_id": self.org.id})

        # -- Assert
        self.assertEqual(200, response.status_code, response.content)
        self.assertEqual(response.content, b"building response")

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template_org_has_no_at_token(self, mock_request):
        # -- Setup
        self.org.at_organization_token = ""
        self.org.save()

        # -- Act
        mock_request.side_effect = [self.good_authenticate_response, self.good_get_building_response]
        response = self.client.get(self.get_building_url, data={"organization_id": self.org.id})

        # -- Assert
        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual(response.json(), {'message': "An Audit Template organization token, user email and password are required!", 'success': False})

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template_bad_at_authentication_response(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.bad_authenticate_response, self.good_get_building_response]
        response = self.client.get(self.get_building_url, data={"organization_id": self.org.id})

        # -- Assert
        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual(
            response.json(),
            {'success': False, 'message': f'Expected 200 response from Audit Template get_api_token but got 400: {self.bad_authenticate_response.content}'}
        )

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template_bad_at_get_building_response(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.good_authenticate_response, self.bad_get_building_response]
        response = self.client.get(self.get_building_url, data={"organization_id": self.org.id})

        # -- Assert
        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual(
            response.json(),
            {'success': False, 'message': f'Expected 200 response from Audit Template get_building_xml but got 400: {self.bad_get_building_response.content}'}
        )


class AuditTemplateBatchTests(TestCase):

    def setUp(self):
        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.org.at_organization_token = "fake at_api_token"
        self.org.audit_template_user = "fake at user"
        self.org.audit_template_password = "fake at password"
        self.org.save()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)

        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone())
        )

        self.client.login(**self.user_details)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.view_factory = FakePropertyViewFactory(organization=self.org)
        self.state_factory = FakePropertyStateFactory(organization=self.org)

        self.state1 = self.state_factory.get_property_state(audit_template_building_id=1)
        self.state2 = self.state_factory.get_property_state(audit_template_building_id=2)
        self.state3 = self.state_factory.get_property_state(audit_template_building_id=3)
        self.state4 = self.state_factory.get_property_state()

        self.view1 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state1)
        self.view2 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state2)
        self.view3 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state3)
        self.view4 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state4)

        self.good_authenticate_response = mock.Mock()
        self.good_authenticate_response.status_code = 200
        self.good_authenticate_response.json = mock.Mock(return_value={"token": "fake token"})

        self.bad_authenticate_response = mock.Mock()
        self.bad_authenticate_response.status_code = 400
        self.bad_authenticate_response.content = {"error": "Invalid email, password or organization_token."}

        self.get_buildings_url = reverse('api:v3:audit_template-get-buildings')
        self.batch_get_xml_url = reverse('api:v3:audit_template-batch-get-building-xml')

        self.good_get_buildings_response = mock.Mock()
        self.good_get_buildings_response.status_code = 200
        self.good_get_buildings_response.json.return_value = [
            {"id": 1, 'name': 'name1', 'updated_at': "2020-01-01T01:00:00.000-07:00"},
            {"id": 2, 'name': 'name2', 'updated_at': "2020-01-01T01:00:00.000-07:00"},
            {"id": 10,'name': 'name3', 'updated_at': "2020-01-01T01:00:00.000-07:00"},  # Should not return id:10
        ]

        self.bad_get_buildings_response = mock.Mock()
        self.bad_get_buildings_response.status_code = 400
        self.bad_get_buildings_response.content = "bad buildings response"

        self.good_batch_xml_response = mock.Mock()
        self.good_batch_xml_response.status_code = 200
        file_path = 'seed/tests/data/building_sync_xml.txt'
        with open(file_path, 'r') as file:
            sample_xml = file.read()
        self.good_batch_xml_response.text = sample_xml.encode().decode('unicode_escape')

    @mock.patch('requests.request')
    def test_get_buildings_from_audit_template(self, mock_request):
        mock_request.side_effect = [self.good_authenticate_response, self.good_get_buildings_response]
        response = self.client.get(self.get_buildings_url, data={'organization_id': self.org.id, 'cycle_id': self.cycle.id})
        self.assertEqual(200, response.status_code)
        response = response.json()

        message = json.loads(response['message'])
        exp_message = [
            {
                'audit_template_building_id': 1,
                'property_view': self.view1.id,
                'email': 'n/a',
                'name': 'name1',
                'updated_at': '2020-01-01 01:00 AM'
            }, {
                'audit_template_building_id': 2,
                'property_view': self.view2.id,
                'email': 'n/a',
                'name': 'name2',
                'updated_at': '2020-01-01 01:00 AM'
            },
        ]
        self.assertEqual(exp_message, message)

    @mock.patch('requests.request')
    def test_get_buildings_from_audit_template_bad_authentication(self, mock_request):
        mock_request.side_effect = [self.bad_authenticate_response, self.good_get_buildings_response]
        response = self.client.get(self.get_buildings_url, data={'organization_id': self.org.id, 'cycle_id': self.cycle.id})
        self.assertEqual(200, response.status_code)
        exp_json = {'success': False, 'message': "Expected 200 response from Audit Template get_api_token but got 400: {'error': 'Invalid email, password or organization_token.'}"}
        self.assertEqual(response.json(), exp_json)

    @mock.patch('requests.request')
    def test_get_buildings_from_audit_template_bad_buildings_response(self, mock_request):
        mock_request.side_effect = [self.good_authenticate_response, self.bad_get_buildings_response]
        response = self.client.get(self.get_buildings_url, data={'organization_id': self.org.id, 'cycle_id': self.cycle.id})

        self.assertEqual(400, response.status_code)
        exp_message = "Expected 200 response from Audit Template get_buildings but got 400: bad buildings response"
        self.assertEqual(response.json()['message'], exp_message)

    @mock.patch('requests.request')
    def test_batch_get_building_xml(self, mock_request):
        mock_request.side_effect = [self.good_authenticate_response, self.good_batch_xml_response, self.good_batch_xml_response]
        url = reverse('api:v3:audit_template-batch-get-building-xml') + '?organization_id=' + str(self.org.id) + '&cycle_id=' + str(self.cycle.id)
        content_type = 'application/json'
        data = json.dumps([
            {'audit_template_building_id': 1, 'property_view': self.view1.id, 'email': 'test@test.com', 'name': 'name1', 'updated_at': '2020-01-01T01:00:00.000000'},
            {'audit_template_building_id': 2, 'property_view': self.view2.id, 'email': 'test@test.com', 'name': 'name2', 'updated_at': '2022-01-01T01:00:00.000000'},
        ])

        response = self.client.put(
            url,
            data=data,
            content_type=content_type
        )
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response['status'], 'success')
        self.assertEqual(response['message'], {'success': 2, 'failure': 0})
        self.assertEqual(response['progress'], 100)

    @mock.patch('requests.request')
    def test_batch_get_building_xml_bad_data(self, mock_request):
        mock_request.side_effect = [self.good_authenticate_response, self.good_batch_xml_response, self.good_batch_xml_response]
        exp_message = "Request data must be structured as: {audit_template_building_id: integer, property_view: integer, email: string, updated_at: date time iso string 'YYYY-MM-DDTHH:MM:SSZ'}"

        # missing property view
        url = reverse('api:v3:audit_template-batch-get-building-xml') + '?organization_id=' + str(self.org.id) + '&cycle_id=' + str(self.cycle.id)
        content_type = 'application/json'
        data = json.dumps([
            {'audit_template_building_id': 1, 'email': 'test@test.com', 'updated_at': '2020-01-01T01:00:00.000000'},
        ])

        response = self.client.put(
            url,
            data=data,
            content_type=content_type
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response['success'], False)
        self.assertEqual(response['message'], exp_message)

        # missing audit tempalte building id
        url = reverse('api:v3:audit_template-batch-get-building-xml') + '?organization_id=' + str(self.org.id) + '&cycle_id=' + str(self.cycle.id)
        content_type = 'application/json'
        data = json.dumps([
            {'property_view': 1, 'email': 'test@test.com', 'updated_at': '2020-01-01T01:00:00.000000'},
        ])

        response = self.client.put(
            url,
            data=data,
            content_type=content_type
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response['success'], False)
        self.assertEqual(response['message'], exp_message)

        # missing email
        url = reverse('api:v3:audit_template-batch-get-building-xml') + '?organization_id=' + str(self.org.id) + '&cycle_id=' + str(self.cycle.id)
        content_type = 'application/json'
        data = json.dumps([
            {'audit_template_building_id': 1, 'property_view': self.view1.id, 'updated_at': '2020-01-01T01:00:00.000000'},
        ])

        response = self.client.put(
            url,
            data=data,
            content_type=content_type
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response['success'], False)
        self.assertEqual(response['message'], exp_message)

        # missing updated_at
        url = reverse('api:v3:audit_template-batch-get-building-xml') + '?organization_id=' + str(self.org.id) + '&cycle_id=' + str(self.cycle.id)
        content_type = 'application/json'
        data = json.dumps([
            {'audit_template_building_id': 1, 'property_view': self.view1.id, 'email': 'test@test.com'},
        ])

        response = self.client.put(
            url,
            data=data,
            content_type=content_type
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response['success'], False)
        self.assertEqual(response['message'], exp_message)

        # extra key
        url = reverse('api:v3:audit_template-batch-get-building-xml') + '?organization_id=' + str(self.org.id) + '&cycle_id=' + str(self.cycle.id)
        content_type = 'application/json'
        data = json.dumps([
            {'invalid': 1, 'audit_template_building_id': 1, 'property_view': self.view1.id, 'updated_at': '2020-01-01T01:00:00.000000'},
        ])

        response = self.client.put(
            url,
            data=data,
            content_type=content_type
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response['success'], False)
        self.assertEqual(response['message'], exp_message)
