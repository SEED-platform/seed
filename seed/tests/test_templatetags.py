# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json

from django.template import Template, Context
from django.test import TestCase


class AppUrlsTest(TestCase):
    """
    Tests of the app_urls templatetag
    """
    def test_app_urls_namespaced_urls(self):
        rendered = Template(
            '{% load app_urls %}'
            '{% namespaced_urls %}'
        ).render(Context())
        rendered = json.loads(rendered)
        self.assertTrue('seed' in rendered.keys())
        self.assertEqual(
            rendered['seed']['get_columns'],
            '/app/get_columns/'
        )
