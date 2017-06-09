# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.models.measures import Measure, _snake_case


class TestException(TestCase):
    def setUp(self):
        pass

    def test_populate_measures(self):
        Measure.populate_measures()
        self.assertEqual(Measure.objects.count(), 174)

        # if we run it again, it shouldn't add anything new
        Measure.populate_measures()
        self.assertEqual(Measure.objects.count(), 174)

    def test_snake_case(self):
        self.assertEqual(_snake_case("AbCdEf"), "ab_cd_ef")
        self.assertEqual(_snake_case("Clean and/or repair"), "clean_and_or_repair")
        self.assertEqual(
            _snake_case("Upgrade operating protocols, calibration, and/or sequencing"),
            "upgrade_operating_protocols_calibration_and_or_sequencing"
        )
        self.assertEqual(_snake_case("AdvancedMeteringSystems"), "advanced_metering_systems")
