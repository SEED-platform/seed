"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.test import TestCase

from seed.landing.models import SEEDUser as User
from seed.models.measures import Measure, _snake_case
from seed.models.property_measures import PropertyMeasure
from seed.utils.organizations import create_organization


class TestMeasures(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("test_user@demo.com", "test_user@demo.com", "test_pass")
        self.org, _, _ = create_organization(self.user)
        Measure.populate_measures(self.org.id)

    def test_populate_measures(self):
        # Populate measure calls for every schema version run automatically when an org is created
        # BuildingSync v1.0.0 has 222 enums
        # BuildingSync v2.6.0 has 329 enums
        # total is 551
        self.assertEqual(Measure.objects.count(), 551)

        # if we run it again, it shouldn't add anything new
        Measure.populate_measures(self.org.id)
        self.assertEqual(Measure.objects.count(), 551)

    def test_snake_case(self):
        self.assertEqual(_snake_case("AbCdEf"), "ab_cd_ef")
        self.assertEqual(_snake_case("Clean and/or repair"), "clean_and_or_repair")
        self.assertEqual(
            _snake_case("Upgrade operating protocols, calibration, and/or sequencing"),
            "upgrade_operating_protocols_calibration_and_or_sequencing",
        )
        self.assertEqual(_snake_case("AdvancedMeteringSystems"), "advanced_metering_systems")

    def test_validate_measures(self):
        measures = [
            ("renewable_energy_systems", "install_photovoltaic_system"),
            ("other_hvac", "add_or_repair_economizer"),
            ("chiller_plant_improvements", "clean_and_or_repair"),
        ]

        objs = []
        for m in measures:
            objs.append(Measure.objects.get(category=m[0], name=m[1], schema_version="2.6.0"))

        obj_ids = [m.id for m in objs]
        obj_names = [f"{m.category}.{m.name}" for m in objs]

        results = Measure.validate_measures(obj_ids)
        self.assertEqual(obj_ids, results)

        results = Measure.validate_measures(obj_names)
        self.assertEqual(obj_ids, results)

        results = Measure.validate_measures(["."])
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

        results = Measure.validate_measures([])
        self.assertEqual(results, [])


class TestPropertyMeasures(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("test_user@demo.com", "test_user@demo.com", "test_pass")
        self.org, _, _ = create_organization(self.user)
        Measure.populate_measures(self.org.id)

        # get some property instances

    def test_lookups(self):
        self.assertEqual(PropertyMeasure.str_to_impl_status(PropertyMeasure.MEASURE_DISCARDED), 5)
        self.assertEqual(PropertyMeasure.str_to_impl_status("measure discarded"), 1)
        self.assertEqual(PropertyMeasure.str_to_impl_status("Discarded"), 5)
        self.assertEqual(PropertyMeasure.str_to_impl_status(None), 1)

        self.assertEqual(PropertyMeasure.str_to_category_affected(PropertyMeasure.CATEGORY_DOMESTIC_HOT_WATER), 5)
        self.assertEqual(PropertyMeasure.str_to_category_affected("domestic nothing"), 27)
        self.assertEqual(PropertyMeasure.str_to_category_affected("Domestic Hot Water"), 5)
        self.assertEqual(PropertyMeasure.str_to_category_affected(None), 27)

        self.assertEqual(PropertyMeasure.str_to_application_scale(PropertyMeasure.SCALE_ENTIRE_FACILITY), 5)
        self.assertEqual(PropertyMeasure.str_to_application_scale("Nothing entirely"), 5)
        self.assertEqual(PropertyMeasure.str_to_application_scale("Entire facility"), 5)
        self.assertEqual(PropertyMeasure.str_to_application_scale(None), 5)
