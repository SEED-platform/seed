# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from datetime import date

from django.test import TestCase

from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle


class TestCycle(TestCase):
    def test_default_cycle(self):
        year = date.today().year - 1
        cycle_name = str(year) + ' Calendar Year'

        self.org = Organization.objects.create()
        self.assertEqual(self.org.cycles.count(), 1)

        cycle = Cycle.objects.filter(name=cycle_name, organization=self.org)
        self.assertEqual(self.org.cycles.count(), 1)
        cycle.delete()
        cycle = Cycle.objects.filter(name=cycle_name, organization=self.org)
        self.assertEqual(self.org.cycles.count(), 0)

        cycle = Cycle.get_or_create_default(self.org)
        self.assertEqual(self.org.cycles.count(), 1)
