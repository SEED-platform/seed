# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging

from django.core.urlresolvers import reverse_lazy, reverse
from django.test import TestCase
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.landing.models import SEEDUser as User
from seed.factory import SEEDFactory
from seed.models import CanonicalBuilding
from seed.utils.api import get_api_endpoints



class ApiAuthenticationTests(TestCase):
    """
    Tests of various ways of authenticating to the API.

    Uses the get_building endpoint in all cases.
    """

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_user(**user_details)
        self.user.generate_key()
        self.org = Organization.objects.create()
        OrganizationUser.objects.create(user=self.user, organization=self.org)

        cb = CanonicalBuilding(active=True)
        cb.save()
        b = SEEDFactory.building_snapshot(canonical_building=cb,
                                          property_name='ADMIN BUILDING',
                                          address_line_1='100 Admin St')
        cb.canonical_snapshot = b
        cb.save()
        b.super_organization = self.org
        b.save()
        self.building = b

        self.api_url = reverse_lazy('seed:get_building')
        self.params = {
            'building_id': cb.pk,
            'organization_id': self.org.pk,
        }
        self.auth_string = '%s:%s' % (self.user.username, self.user.api_key)

    def test_get(self):
        """
        Test auth via GET parameter.
        """
        headers = {'HTTP_AUTHORIZATION': self.auth_string}
        resp = self.client.get(self.api_url, data=self.params, **headers)
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertEqual(body['status'], 'success')
        self.assertEqual(body['building']['address_line_1'],
                         self.building.address_line_1)

    def test_no_auth(self):
        """
        Test forgetting to provide API key in any form.
        """
        resp = self.client.get(self.api_url, data=self.params)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.content, '')


class SchemaGenerationTests(TestCase):

    def test_get_api_endpoints_utils(self):
        """
        Test of function that traverses all urls looking for api endpoints.
        """
        res = get_api_endpoints()
        for url, fn in res.items():
            self.assertTrue(fn.is_api_endpoint)
            self.assertTrue(url.startswith('/'))
            self.assertTrue(url.endswith('/'),
                            "Endpoint %s doesn't end with / as expected" % url)

    def test_get_api_schema(self):
        """
        Test of 'schema' generator.
        """
        url = reverse('api:get_api_schema')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        endpoints = json.loads(res.content)

        #the url we just hit should be in here
        self.assertTrue(url in endpoints)
        endpoint = endpoints[url]
        self.assertEqual(endpoint['name'], 'get_api_schema')
        self.assertTrue('description' in endpoint)

