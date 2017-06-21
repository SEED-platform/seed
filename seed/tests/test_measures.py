# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.test import TestCase

from seed.models.measures import Measure, _snake_case


class TestMeasures(TestCase):
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

    def test_validate_measures(self):
        Measure.populate_measures()

        measures = [
            ("renewable_energy_systems", "install_photovoltaic_system"),
            ("other_hvac", "add_or_repair_economizer"),
            ("chiller_plant_improvements", "clean_and_or_repair")
        ]

        objs = []
        for m in measures:
            objs.append(Measure.objects.get(category=m[0], name=m[1]))

        obj_ids = [m.id for m in objs]
        obj_names = ["{}.{}".format(m.category, m.name) for m in objs]

        results = Measure.validate_measures(obj_ids)
        self.assertEqual(obj_ids, results)

        results = Measure.validate_measures(obj_names)
        self.assertEqual(obj_ids, results)

        results = Measure.validate_measures(['.'])
        self.assertEqual([], results)

        extra_blank = list(obj_ids)
        extra_blank.append("")
        results = Measure.validate_measures(extra_blank)
        self.assertEqual(obj_ids, results)

        extra_malformed = list(obj_ids)
        extra_malformed.append("abcdef")
        results = Measure.validate_measures(extra_malformed)
        self.assertEqual(obj_ids, results)

        extra_missing = list(obj_ids)
        extra_missing.append("a.b")
        results = Measure.validate_measures(extra_missing)
        self.assertEqual(obj_ids, results)
