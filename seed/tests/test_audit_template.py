# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
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

        self.good_authenticate_reponse = mock.Mock()
        self.good_authenticate_reponse.status_code = 200
        self.good_authenticate_reponse.json = mock.Mock(return_value={"token": "fake token"})

        self.bad_authenticate_reponse = mock.Mock()
        self.bad_authenticate_reponse.status_code = 400
        self.bad_authenticate_reponse.content = {"error": "Invalid email, password or organization_token."}

        self.good_get_building_reponse = mock.Mock()
        self.good_get_building_reponse.status_code = 200
        self.good_get_building_reponse.text = "building reponse"

        self.bad_get_building_reponse = mock.Mock()
        self.bad_get_building_reponse.status_code = 400
        self.bad_get_building_reponse.content = "bad building reponse"

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.good_authenticate_reponse, self.good_get_building_reponse]
        response = self.client.get(self.get_building_url)

        # -- Assert
        self.assertEqual(200, response.status_code, response.content)
        self.assertEqual(response.content, b"building reponse")

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template_org_has_no_at_token(self, mock_request):
        # -- Setup
        self.org.at_organization_token = ""
        self.org.save()

        # -- Act
        mock_request.side_effect = [self.good_authenticate_reponse, self.good_get_building_reponse]
        response = self.client.get(self.get_building_url)

        # -- Assert
        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual(response.json(), {'message': "An Audit Template organization token, user email and password are required!", 'success': False})

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template_bad_at_authentication_response(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.bad_authenticate_reponse, self.good_get_building_reponse]
        response = self.client.get(self.get_building_url)

        # -- Assert
        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual(
            response.json(),
            {'success': False, 'message': f'Expected 200 response from Audit Template but got 400: {self.bad_authenticate_reponse.content}'}
        )

    @mock.patch('requests.request')
    def test_get_building_xml_from_audit_template_bad_at_get_building_response(self, mock_request):
        # -- Act
        mock_request.side_effect = [self.good_authenticate_reponse, self.bad_get_building_reponse]
        response = self.client.get(self.get_building_url)

        # -- Assert
        self.assertEqual(400, response.status_code, response.content)
        self.assertEqual(
            response.json(),
            {'success': False, 'message': f'Expected 200 response from Audit Template but got 400: {self.bad_get_building_reponse.content}'}
        )
