"""
:copyright: (c) 2014 Building Energy Inc
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
            '/main/app/get_columns/'
        )
