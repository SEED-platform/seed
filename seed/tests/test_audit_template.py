# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import mock
from django.test import TestCase
from django.urls import reverse

from seed.landing.models import SEEDUser as User
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

        self.get_building_url = reverse('api:v3:audit_template-get-building-xml', args=["1"])

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
            {'success': False, 'message': f'Expected 200 response from Audit Template but got 400: {self.bad_authenticate_response.content}'}
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
            {'success': False, 'message': f'Expected 200 response from Audit Template but got 400: {self.bad_get_building_response.content}'}
        )
