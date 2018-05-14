# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author Paul Munday <paul@paulmunday.net>
"""
import json

from django.core.urlresolvers import reverse_lazy
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.utils.organizations import create_organization
from seed.views.portfoliomanager import PortfolioManagerImport


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


class PortfolioManagerViewTests(TestCase):
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
            reverse_lazy('api:v2.1:portfolio_manager-template-list'),
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
            reverse_lazy('api:v2.1:portfolio_manager-template-list'),
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

    def test_template_list_invalid_credentials(self):
        resp = self.client.post(
            reverse_lazy('api:v2.1:portfolio_manager-template-list'),
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

    def test_report_interface_no_username(self):
        resp = self.client.post(
            reverse_lazy('api:v2.1:portfolio_manager-report'),
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
            reverse_lazy('api:v2.1:portfolio_manager-report'),
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
            reverse_lazy('api:v2.1:portfolio_manager-report'),
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

    def test_report_invalid_credentials(self):
        resp = self.client.post(
            reverse_lazy('api:v2.1:portfolio_manager-report'),
            json.dumps({'password': 'nothing', 'username': 'nothing', 'template': {'id': 1, 'name': 'template_name'}}),
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
