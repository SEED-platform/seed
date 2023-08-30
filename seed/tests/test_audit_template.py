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
from django.conf import settings
from django.utils import timezone
import requests
import xml.etree.ElementTree as ET
import io
import xmltodict
from lxml import etree

from seed.landing.models import SEEDUser as User
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory
)
from seed.utils.organizations import create_organization
# from seed.audit_template.audit_template import build_xml
from seed.audit_template.audit_template import AuditTemplate


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


# class ExportToAuditTemplate
class eat(TestCase):
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
        self.org.at_organization_token = "eJiZ6qZSSk88sCnTZLhc"
        self.org.audit_template_user = "ross.perry@deptagency.com"
        self.org.audit_template_password = "ATpass1!"
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
            audit_template_building_id=1,
            property_name='property1',
            address_line_1='123 Street Ave',
            gross_floor_area=1000,
            city='Denver',
            state='CO',
            postal_code='80209',
            year_built=2000,

        )
        self.state_ny = self.state_factory.get_property_state(
            property_name='property1',
            address_line_1='123 Street Ave',
            gross_floor_area=1000,
            city='New York',
            state='NY',
            postal_code='80209',
            year_built=2000,
        )
        self.state3 = self.state_factory.get_property_state(audit_template_building_id=3)
        self.state4 = self.state_factory.get_property_state()

        self.view1 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state1)
        self.view2 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state_ny)
        self.view3 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state3)
        self.view4 = self.view_factory.get_property_view(cycle=self.cycle, state=self.state4)

    def get_token(self):
        json = {
            'organization_token': 'eJiZ6qZSSk88sCnTZLhc',
            'email': 'ross.perry@deptagency.com',
            'password': 'ATpass1!'
        }
        headers = {"Content-Type": "application/json; charset=utf-8", 'accept': 'application/xml'}
        response = requests.request("POST", self.token_url, headers=headers, json=json)
        self.assertEqual(200, response.status_code)
        return response.json()['token']

    def test_export_to_AT1(self):
        """
        Export to Audit Template with a known xml file.
        convert xml to an xml_string then send as a file-like object
        """
        # get at token 
        token = self.get_token()
        # use response token in export request
   

        # Creating an xml string from an xml fixture
        # in practice it will be created from a dictionary
        xml_path = 'seed/tests/data/minimum_bsync_for_at_upload.xml'
        xml_path = 'seed/tests/data/test_ny_from_at.xml'
        tree = ET.parse(xml_path)
        root = tree.getroot()
        xml_string = ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')
        # ---------------------


        # --------------------
        # Probably the cleanest option
        files = {'audit_file': ('at_export.xml', xml_string)}
        body = {'token': token}

        response = requests.post(self.upload_url, data=body, files=files)
        self.assertEqual(200, response.status_code)

    def test_export_to_AT2(self):
        """
        Export to Audit Template with built xml file
        """
        report_types = [
            'ASHRAE Level 2 Report',
            'Atlanta Report',
            'Berkeley Report',
            'BRICR Phase 0/1',
            'Brisbane Energy Audit Report',
            'DC BEPS Energy Audit Report',
            'DC BEPS RCx Report',
            'Demo City Report',
            'Denver Energy Audit Report',
            'Energy Trust of Oregon Report',
            'Minneapolis Energy Evaluation Report',
            # 'New York City Energy Efficiency Report',  # always returns 422 'Rp nyc property can't be blank'
            'Open Efficiency Report',
            'San Francisco Report',
            'WA Commerce Clean Buildings - Form D Report',
            'WA Commerce Grants Report',
        ]
        token = self.get_token()
        status_codes = {}
        for report in report_types:
            xml_string = ''
            # xml_string, _ = build_xml(self.state1, report)

            
            files = {'audit_file': ('at_export.xml', xml_string)}
            body = {'token': token}
            response = requests.post(self.upload_url, data=body, files=files)
            status_codes[report] = response.status_code

        breakpoint()

   

    def test_export_to_AT4(self):
        """
        Export to audit template. This is using real data that needs to be mocked out.
        """
        at = AuditTemplate(self.org.id)
        response, error_ = at.export_to_audit_template(self.state1)
        self.assertEqual(200, response.status_code)

        
        breakpoint()
        

        # ---------------------------------------------------------------------
        # --------------------------- attempts --------------------------------
        # ---------------------------------------------------------------------

        # token = self.get_token()
        # xml_string, _ = build_xml(self.state1, 'ASHRAE Level 2 Report')
        # files = {'audit_file': ('at_export.xml', xml_string)}
        # body = {'token': token}

        # Write xml to test data dir
        # xml_path = 'seed/tests/data/test_rp2.xml'
        # with open(xml_path, 'w') as f:
        #     f.write(xml_string)

        # response = requests.post(self.upload_url, data=body, files=files)
        # self.assertEqual(200, response.status_code)


        # root = ET.fromstring(xml_string)
        # namespaces = {'ns0': 'http://buildingsync.net/schemas/bedes-auc/2019'}

        # def process_element(element, parent_dict):
        #     child_dict = {}
        #     for child in element:
        #         process_element(child, child_dict)
        #     parent_dict[element.tag.split('}')[-1]] = element.text if not child_dict else child_dict


        # xml_dict = {}
        # process_element(root, xml_dict)

        # xml_path = 'seed/tests/data/test_rp.xml'
        # with open(xml_path, 'w') as f:
        #     f.write(xml_string)

        # --------------

        # def dict_to_xml(tag, data, nsmap=None):
        #     if ':' in tag:
        #         ns, tag = tag.split(':', 1)
        #         elm = etree.Element("{%s}%s" % (nsmap[ns], tag), nsmap=nsmap)
        #     else:
        #         elm = etree.Element(tag, nsmap=nsmap)

        #     for key, val in data.items():
        #         child = etree.Element(key)
        #         if isinstance(val, dict):
        #             child.append(dict_to_xml(key, val))
        #         else:
        #             child.text = str(val)
        #         elm.append(child)
        #     return elm


        # nsmap = {'ns0': 'http://buildingsync.net/schemas/bedes-auc/2019'}
        # root = dict_to_xml('ns0:BuildingSync', xml_dict, nsmap)
        # root.set('version', '2.3.0')
        # xs = etree.tostring(root, pretty_print=True).decode()
        # breakpoint()


        # # Convert dictionary to lxml Element
        # root = dict_to_xml('ns0:BuildingSync', xml_dict)

        # # Add the namespace
        # root.set('xmlns:ns0', 'http://buildingsync.net/schemas/bedes-auc/2019')
        # root.set('version', '2.3.0')

        # xml_string2 = etree.tostring(root, pretty_print=True).decode()



        # x = {child.tag: child.text for child in root}
        # breakpoint()


