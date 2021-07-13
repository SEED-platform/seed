# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
import json
import os
import requests
from unittest import skip, skipIf

from django.urls import reverse_lazy
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.utils.organizations import create_organization
from seed.views.portfoliomanager import PortfolioManagerImport


PM_UN = 'SEED_PM_UN'
PM_PW = 'SEED_PM_PW'
pm_skip_test_check = skipIf(
    not os.environ.get(PM_UN, False) and not os.environ.get(PM_PW, False),
    'Cannot run "expect-pass" PM unit tests without %s and %s in environment' % (PM_UN, PM_PW)
)

# override this decorator for more pressing conditions
try:
    pm_avail_check = requests.get('http://isthewallbuilt.inbelievable.com/api.json', timeout=5)
    string_response = pm_avail_check.json()['status']
    if string_response != 'no':
        skip_due_to_espm_down = False
    else:
        skip_due_to_espm_down = True

    if skip_due_to_espm_down:
        pm_skip_test_check = skip('ESPM is likely down temporarily, ESPM tests will not run')
except Exception:
    pass


class PortfolioManagerImportTest(TestCase):
    def test_unsuccessful_login(self):
        # To test a successful login, we'd have to include valid PM credentials, which we don't want to do
        # so I will at least test an unsuccessful login attempt here
        pmi = PortfolioManagerImport('bad_username', 'bad_password')
        with self.assertRaises(Exception):
            pmi.login_and_set_cookie_header()

    def test_get_template_by_name(self):
        template_1 = {'id': 1, 'name': 'first'}
        template_2 = {'id': 2, 'name': 'second'}
        template_set = [template_1, template_2]
        self.assertDictEqual(template_1, PortfolioManagerImport.get_template_by_name(template_set, 'first'))
        self.assertDictEqual(template_2, PortfolioManagerImport.get_template_by_name(template_set, 'second'))
        with self.assertRaises(Exception):
            PortfolioManagerImport.get_template_by_name(template_set, 'missing')


class PortfolioManagerTemplateListViewTestsFailure(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

    def tearDown(self):
        self.user.delete()
        self.org.delete()

    def test_template_list_interface_no_username(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-template-list'),
            json.dumps({'password': 'nothing'}),
            content_type='application/json'
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing username"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('missing username', data['message'])

    def test_template_list_interface_no_password(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-template-list'),
            json.dumps({'username': 'nothing'}),
            content_type='application/json',
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing password"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('missing password', data['message'])

    @pm_skip_test_check
    def test_template_list_invalid_credentials(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-template-list'),
            json.dumps({'password': 'nothing', 'username': 'nothing'}),
            content_type='application/json',
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing template"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('Check credentials.', data['message'])


class PortfolioManagerTemplateListViewTestsSuccess(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

    @pm_skip_test_check
    def test_template_views(self):
        # if we get into this test, the PM_UN and PM_PW variables should be available
        # we'll still check of course
        pm_un = os.environ.get(PM_UN, False)
        pm_pw = os.environ.get(PM_PW, False)
        if not pm_un or not pm_pw:
            self.fail('Somehow PM test was initiated without %s or %s in the environment' % (PM_UN, PM_PW))

        # so now we'll make the call out to PM
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-template-list'),
            json.dumps({'username': pm_un, 'password': pm_pw}),
            content_type='application/json',
        )
        # this kinda gets a little fragile here.
        # We can't really guarantee that the test account over on ESPM will stay exactly like it is the whole time
        # But we can try to at least test the "form" of the response to make sure it is what we expect
        # And if we ever break the stuff over on ESPM it should be clear what went wrong

        # at a minimum, we should have a successful login and response
        self.assertEqual(200, resp.status_code)

        # the body should come as json; if not, this will fail to parse I presume and fail this test
        body = resp.json()

        # body should represent the successful process
        self.assertTrue(body['status'])

        # templates should be present, and be a list
        self.assertIn('templates', body)
        self.assertIsInstance(body['templates'], list)

        # every object in that list should be a dictionary that contains a bunch of expected keys
        for row in body['templates']:
            for expected_key in ['name', 'display_name', 'z_seed_child_row']:
                self.assertIn(expected_key, row)

            # if it is a child (data request) row, the display name should be formatted
            # it is possible that a parent row could have the same "indentation", and that's fine, we don't assert there
            if row['z_seed_child_row']:
                self.assertEqual('  -  ', row['display_name'][0:5])


class PortfolioManagerReportGenerationViewTestsFailure(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

    def test_report_interface_no_username(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps({'password': 'nothing', 'template': 'nothing'}),
            content_type='application/json',
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing username"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('missing username', data['message'])

    def test_report_interface_no_password(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps({'username': 'nothing', 'template': 'nothing'}),
            content_type='application/json',
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing password"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('missing password', data['message'])

    def test_report_interface_no_template(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps({'password': 'nothing', 'username': 'nothing'}),
            content_type='application/json',
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing template"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('missing template', data['message'])

    @pm_skip_test_check
    def test_report_invalid_credentials(self):
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps(
                {
                    'password': 'nothing',
                    'username': 'nothing',
                    'template': {
                        'id': 1, 'name': 'template_name', 'z_seed_child_row': False
                    }
                }
            ),
            content_type='application/json',
        )
        # resp should have status, message, and code = 400
        # status should be error
        # message should have "missing template"
        self.assertEqual(400, resp.status_code)
        data = json.loads(resp.content)
        self.assertIn('status', data)
        self.assertIn('message', data)
        self.assertEqual('error', data['status'])
        self.assertIn('Check credentials.', data['message'])


class PortfolioManagerReportGenerationViewTestsSuccess(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com',
            'first_name': 'Johnny',
            'last_name': 'Energy',
        }
        self.user = User.objects.create_user(**user_details)
        self.org, self.org_user, _ = create_organization(self.user)
        self.client.login(**user_details)

        # if we get into this test, the PM_UN and PM_PW variables should be available
        # we'll still check of course
        self.pm_un = os.environ.get(PM_UN, False)
        self.pm_pw = os.environ.get(PM_PW, False)
        if not self.pm_un or not self.pm_pw:
            self.fail('Somehow PM test was initiated without %s or %s in the environment' % (PM_UN, PM_PW))

    @pm_skip_test_check
    def test_report_generation_parent_template(self):

        parent_template = {
            'display_name': 'SEED City Test Report',
            'name': 'SEED City Test Report',
            'id': 1103344,
            'z_seed_child_row': False,
            'type': 0,
            'children': [],
            'pending': 0
        }

        # so now we'll call out to PM to get a parent template report
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps({'username': self.pm_un, 'password': self.pm_pw, 'template': parent_template}),
            content_type='application/json',
        )

        # as usual, the first thing to test is really the status code of the response
        self.assertEqual(200, resp.status_code)

        # and we expect a json blob to come back
        body = resp.json()

        # the status flag should be successful
        self.assertEqual('success', body['status'])

        # we expect a list of properties to come back
        self.assertIn('properties', body)
        self.assertIsInstance(body['properties'], list)

        # then for each property, we expect some keys to come back, but if it has the property id, that should suffice
        for prop in body['properties']:
            self.assertIn('property_id', prop)

    @pm_skip_test_check
    def test_report_generation_empty_child_template(self):

        child_template = {
            'display_name': '  -  Data Request:SEED City Test Report April 24 2018',
            'name': 'Data Request:SEED City Test Report April 24 2018',
            'id': 2097417,
            'subtype': 2,
            'z_seed_child_row': True,
            'hasChildrenRows': False,
            'type': 1,
            'children': [],
            'pending': 0
        }

        # so now we'll call out to PM to get a child template report
        resp = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps({'username': self.pm_un, 'password': self.pm_pw, 'template': child_template}),
            content_type='application/json',
        )

        # this child template is empty over on PM, so it comes back as a 400
        self.assertEqual(400, resp.status_code)

        # still, we expect a json blob to come back
        body = resp.json()

        # the status flag should be error
        self.assertEqual('error', body['status'])

        # in this case, we expect a meaningful error message
        self.assertIn('message', body)
        self.assertIn('empty', body['message'])


class PortfolioManagerReportSinglePropertyUploadTest(TestCase):

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

        # create a dataset
        dataset_name = 'test_dataset'
        response = self.client.post(
            reverse_lazy('api:v3:datasets-list') + '?organization_id=' + str(self.org.pk),
            data=json.dumps({'name': dataset_name}),
            content_type='application/json',
        )
        dataset = response.json()
        self.dataset_id = dataset['id']

        self.pm_un = os.environ.get(PM_UN, False)
        self.pm_pw = os.environ.get(PM_PW, False)
        if not self.pm_un or not self.pm_pw:
            self.fail('Somehow PM test was initiated without %s or %s in the environment' % (PM_UN, PM_PW))

    @pm_skip_test_check
    def test_single_property_template_for_upload(self):

        # create a single property report with template
        template = {
            "children": [],
            "display_name": "SEED_Test - Single Property",
            "id": 2807325,
            "name": "SEED_Test - Single Property",
            "newReport": 0,
            "z_seed_child_row": 0
        }

        report_response = self.client.post(
            reverse_lazy('api:v3:portfolio_manager-report'),
            json.dumps({"username": self.pm_un, "password": self.pm_pw, "template": template}),
            content_type='application/json',
        )
        self.assertEqual(200, report_response.status_code)

        property_info = json.loads(report_response.content)
        self.assertEqual(1, len(property_info['properties']))
        self.assertIsInstance(property_info['properties'], list)

        # add report to dataset
        response = self.client.post(
            reverse_lazy('api:v3:upload-create-from-pm-import'),
            json.dumps({
                'properties': property_info['properties'],
                'import_record_id': self.dataset_id,
                'organization_id': self.org.pk}),
            content_type='application/json',
        )
        self.assertEqual(200, response.status_code)
