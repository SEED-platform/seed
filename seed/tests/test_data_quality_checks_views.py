# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json

from django.urls import reverse
from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.utils.organizations import create_organization


class DataQualityViewTests(TestCase):
    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.user = User.objects.create_superuser(**user_details)
        self.org, _, _ = create_organization(self.user)
        self.client.login(**user_details)

    def test_get_datasets(self):
        # check to make sure the data quality data exist
        url = reverse('api:v2:data_quality_checks-data-quality-rules')
        response = self.client.get(url, {'organization_id': self.org.pk})
        jdata = json.loads(response.content)
        self.assertEqual(jdata['status'], 'success')
        self.assertEqual(len(jdata['rules']['taxlots']), 2)
        self.assertEqual(len(jdata['rules']['properties']), 20)
