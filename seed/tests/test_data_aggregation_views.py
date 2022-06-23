# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.test import TestCase
from django.urls import reverse


class DataAggregationViewTests(TestCase):

    def test_pass(self):
        assert 1 == 1

    def test_create_data_aggregation(self):
        url = reverse('api:v3:data-aggregation', args=[])
        response = self.client.post(reverse(url, content_type='application/json'))
        # breakpoint()
