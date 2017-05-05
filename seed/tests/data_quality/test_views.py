# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase

from seed.landing.models import SEEDUser as User

_log = logging.getLogger(__name__)


class DataQualityViewTests(TestCase):

    def setUp(self):
        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
        }
        self.user = User.objects.create_superuser(email='test_user@demo.com', **user_details)
        self.client.login(**user_details)

    def test_get_data_quality_results(self):
        data = {'test': 'test'}
        cache.set('data_quality_results__1', data)
        response = self.client.get(reverse('apiv2:import_files-data-quality-results', args=[1]))
        self.assertEqual(json.loads(response.content)['data'], data)

    def test_get_progress(self):
        data = {'status': 'success', 'progress': 85}
        cache.set(':1:SEED:get_progress:PROG:1', data)
        response = self.client.get(reverse('apiv2:import_files-data-quality-progress', args=[1]))
        self.assertEqual(json.loads(response.content), 85)

    def test_get_csv(self):
        data = [{
            'address_line_1': '',
            'pm_property_id': '',
            'tax_lot_id': '',
            'custom_id_1': '',
            'data_quality_results': [{
                'formatted_field': '',
                'detailed_message': '',
                'severity': '',
            }]
        }]
        cache.set('data_quality_results__1', data)
        response = self.client.get(reverse('apiv2:import_files-data-quality-results-csv', args=[1]))
        self.assertEqual(200, response.status_code)
