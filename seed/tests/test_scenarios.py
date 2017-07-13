# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.models.scenarios import Scenario
from seed.models import Organization


class TestMeasures(TestCase):
    def setUp(self):
        self.org = Organization.objects.create()

    def tearDown(self):
        Scenario.objects.all().delete()

    def test_scenario_meters(self):

        s = Scenario.objects.create(
            name='Test'
        )

        # create a new meter
        # s.meters.add()


