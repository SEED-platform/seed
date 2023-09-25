"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.test import TestCase
from django.urls import reverse


class RobotsTests(TestCase):
    def test_robots(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(200, response.status_code)
