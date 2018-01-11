# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from seed.models import Organization
from seed.test_helpers.fake import FakePropertyMeasureFactory
from seed.tests.util import DeleteModelsTestCase


class TestMeasures(DeleteModelsTestCase):
    def setUp(self):
        self.org = Organization.objects.create()

    def test_scenario_meters(self):
        ps = FakePropertyMeasureFactory(self.org).get_property_state()

        self.assertEqual(ps.measures.count(), 5)
        self.assertEqual(ps.propertymeasure_set.count(), 5)

        # for m in ps.propertymeasure_set.all():
        #     print m.measure
        #     print m.cost_mv

        # s = Scenario.objects.create(
        #     name='Test'
        # )
        # s.property_state = ps
        # s.save()

        # create a new meter
        # s.meters.add()
