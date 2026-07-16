"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import TestCase
from django.urls import reverse


class RobotsTests(TestCase):
    def test_robots(self):
        response = self.client.get(reverse("robots_txt"))
        self.assertEqual(200, response.status_code)
