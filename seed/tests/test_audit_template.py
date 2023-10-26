# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

import mock
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

# from seed.audit_template.audit_template import build_xml
from seed.audit_template.audit_template import AuditTemplate
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
            {"id": 10, 'name': 'name3', 'updated_at': "2020-01-01T01:00:00.000-07:00"},  # Should not return id:10
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


class ExportToAuditTemplate(TestCase):
    def setUp(self):
        HOST = settings.AUDIT_TEMPLATE_HOST
        self.API_URL = f'{HOST}/api/v2'
        self.token_url = f'{self.API_URL}/users/authenticate'
        self.upload_url = f'{self.API_URL}/building_sync/upload'

        self.user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(
            email='test_user@demo.com', **self.user_details
        )
        self.org, _, _ = create_organization(self.user)
        self.org.at_organization_token = "fake"
        self.org.audit_template_user = "fake@.com"
        self.org.audit_template_password = "fake"
        self.org.property_display_field = 'pm_property_id'
        self.org.save()
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)

        self.cycle = self.cycle_factory.get_cycle(
            start=datetime(2010, 10, 10, tzinfo=timezone.get_current_timezone())
        )

        self.client.login(**self.user_details)
        self.property_factory = FakePropertyFactory(organization=self.org)
        self.view_factory = FakePropertyViewFactory(organization=self.org)
        self.state_factory = FakePropertyStateFactory(organization=self.org)

        self.state1 = self.state_factory.get_property_state(
            property_name='property1',
            address_line_1='111 One St',
            gross_floor_area=1000,
            city='Denver',
            state='CO',
            postal_code='80209',
            year_built=2000,

        )
        self.state2 = self.state_factory.get_property_state(
            property_name='property ny',
            address_line_1='222 Two St',
            gross_floor_area=1000,
            city='New York',
            state='NY',
            postal_code='80209',
            year_built=2000,
        )
        # missing required fields
        self.state3 = self.state_factory.get_property_state(address_line_1=None)
        # existing audit_template_building_id (will be ignored)
        self.state4 = self.state_factory.get_property_state(
            audit_template_building_id='4444',
            property_name='property 4',
            address_line_1='444 Four St',
            gross_floor_area=1000,
            city='Denver',
            state='CO',
            postal_code='80209',
            year_built=2000
        )

        self.view1 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state1)
        self.view2 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state2)
        self.view3 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state3)
        self.view4 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state4)

    def test_build_xml_from_property(self):
        """
        Properties must be exported to Audit Template as an XML
        """
        at = AuditTemplate(self.org.id)
        response1 = at.build_xml(self.state1, 'Demo City Report', self.state1.pm_property_id)
        response2 = at.build_xml(self.state2, 'Demo City Report', self.state2.pm_property_id)
        # property missing required fields
        response3 = at.build_xml(self.state3, 'Demo City Report', self.state3.pm_property_id)

        self.assertEqual(tuple, type(response1))
        self.assertEqual(tuple, type(response2))
        self.assertEqual(tuple, type(response3))

        exp = '<auc:BuildingSync'
        self.assertEqual(str, type(response1[0]))
        self.assertEqual(exp, response1[0][:17])
        self.assertTrue('111 One St' in response1[0])
        self.assertFalse('222 Two St' in response1[0])

        self.assertEqual(str, type(response2[0]))
        self.assertEqual(exp, response2[0][:17])
        self.assertFalse('111 One St' in response2[0])
        self.assertTrue('222 Two St' in response2[0])

        self.assertEqual([], response1[1])
        self.assertEqual([], response2[1])

        # property missing required fields
        self.assertIsNone(response3[0])
        messages = response3[1]
        exp_error = f'Validation Error. {self.state3.pm_property_id} must have address_line_1, property_name'
        self.assertEqual('error', messages[0])
        self.assertEqual(exp_error, messages[1])

    @mock.patch('requests.request')
    def test_export_to_audit_template(self, mock_request):
        """
        Converts properties to xmls and exports to Audit Template
        """

        at = AuditTemplate(self.org.id)
        token = 'fake token'

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = json.return_value = {'rp_buildings': {'BuildingType-1': 'https://fake.gov/rp/buildings/1111'}, 'rp_nyc_properties': {}}
        mock_request.return_value = mock_response

        # existing property
        response, messages = at.export_to_audit_template(self.state4, token)
        self.assertIsNone(response)
        exp = ['info', f'{self.state4.pm_property_id}: Existing Audit Template Property']
        self.assertEqual(exp, messages)

        # invalid property
        response, messages = at.export_to_audit_template(self.state3, token)
        self.assertIsNone(response)
        exp = ['error', f'Validation Error. {self.state3.pm_property_id} must have address_line_1, property_name']
        self.assertEqual(exp, messages)

        # valid property
        response, messages = at.export_to_audit_template(self.state1, token)
        self.assertEqual([], messages)
        exp = {'rp_buildings': {'BuildingType-1': 'https://fake.gov/rp/buildings/1111'}, 'rp_nyc_properties': {}}
        self.assertEqual(exp, response.json())

    @mock.patch('requests.request')
    def test_batch_export_to_audit_template(self, mock_request):
        """
        Exports multiple properties to Audit Template
        """
        at = AuditTemplate(self.org.id)

        mock_authenticate_response = mock.Mock()
        mock_authenticate_response.status_code = 200
        mock_authenticate_response.json.return_value = {'token': 'fake token'}

        mock_export1_response = mock.Mock()
        mock_export1_response.status_code = 200
        mock_export1_response.json.return_value = {'rp_buildings': {'BuildingType-1': 'https://fake.gov/rp/buildings/1111'}, 'rp_nyc_properties': {}}

        mock_export2_response = mock.Mock()
        mock_export2_response.status_code = 200
        mock_export2_response.json.return_value = {'rp_buildings': {'BuildingType-1': 'https://fake.gov/rp/buildings/2222'}, 'rp_nyc_properties': {}}
        mock_request.side_effect = [mock_authenticate_response, mock_export1_response, mock_export2_response]

        # check status of audit_template_building_ids
        self.assertIsNone(self.state1.audit_template_building_id)
        self.assertIsNone(self.state2.audit_template_building_id)
        self.assertIsNone(self.state3.audit_template_building_id)
        self.assertEqual('4444', self.state4.audit_template_building_id)

        results, _ = at.batch_export_to_audit_template([self.view1.id, self.view2.id, self.view3.id, self.view4.id])
        message = results['message']
        self.assertEqual(['error', 'info', 'success'], sorted(list(message.keys())))
        # refresh data
        self.state1.refresh_from_db()
        self.state2.refresh_from_db()
        self.state3.refresh_from_db()
        self.state4.refresh_from_db()

        success = message['success']
        info = message['info']
        error = message['error']

        self.assertEqual(2, success['count'])
        self.assertEqual(1, info['count'])
        self.assertEqual(1, error['count'])

        details = success['details']
        self.assertEqual(self.view1.id, details[0]['view_id'])
        self.assertEqual('1111', details[0]['at_building_id'])
        self.assertEqual('1111', self.state1.audit_template_building_id)

        self.assertEqual(self.view2.id, details[1]['view_id'])
        self.assertEqual('2222', success['details'][1]['at_building_id'])
        self.assertEqual('2222', self.state2.audit_template_building_id)

        details = error['details']
        exp = f'Validation Error. {self.state3.pm_property_id} must have address_line_1, property_name'
        self.assertEqual(self.view3.id, details[0]['view_id'])
        self.assertEqual(exp, details[0]['message'])
        self.assertIsNone(self.state3.audit_template_building_id)

        details = info['details']
        exp = f'{self.state4.pm_property_id}: Existing Audit Template Property'
        self.assertEqual(self.view4.id, details[0]['view_id'])
        self.assertEqual(exp, details[0]['message'])
        self.assertEqual('4444', self.state4.audit_template_building_id)
