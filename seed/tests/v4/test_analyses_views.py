"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.models import Column, Unit
from seed.test_helpers.fake import (
    FakeCycleFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import AccessLevelBaseTestCase


class TestAnalysisViews(AccessLevelBaseTestCase):
    def setUp(self):
        super().setUp()
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)
        self.cycle_factory = FakeCycleFactory(organization=self.org)
        self.cycle = self.cycle_factory.get_cycle()

        Column.objects.create(table_name="PropertyState", column_name="extra_field", organization=self.org, is_extra_data=True)
        float_unit = Unit.objects.create(unit_name="kBtu", unit_type=Unit.FLOAT)
        Column.objects.create(
            table_name="PropertyState",
            column_name="extra_numeric",
            organization=self.org,
            is_extra_data=True,
            data_type="float",
            unit=float_unit,
            units_pint="kBtu",
        )

        gfa_values_without_extra_data = [10, 20, 30, 40, 50]
        for gfa in gfa_values_without_extra_data:
            state = self.property_state_factory.get_property_state(gross_floor_area=gfa)
            self.property_view_factory.get_property_view(cycle=self.cycle, state=state)
        gfa_values_with_extra_data = [1, 2, 3, 4, 5]
        for i, gfa in enumerate(gfa_values_with_extra_data):
            details = {
                "custom_id_1": i,
                "extra_data": {"extra_field": f"extra {i}", "extra_numeric": (i + 1) * 10},
                "gross_floor_area": gfa,
            }
            state = self.property_state_factory.get_property_state(**details)
            self.property_view_factory.get_property_view(cycle=self.cycle, state=state)
        self.expected_total_sqft = sum(gfa_values_without_extra_data) + sum(gfa_values_with_extra_data)

    def test_column_summary_can_span_multiple_cycles(self):
        second_cycle = self.cycle_factory.get_cycle()
        second_cycle_gfa_values = [100, 200]
        for gfa in second_cycle_gfa_values:
            state = self.property_state_factory.get_property_state(gross_floor_area=gfa)
            self.property_view_factory.get_property_view(cycle=second_cycle, state=state)

        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id},{second_cycle.id}"
            + "&column_names=gross_floor_area"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["selected_cycle_ids"], [self.cycle.id, second_cycle.id])
        self.assertEqual(payload["total_records"], 12)

        cycle_records = {c["cycle_id"]: c["total_records"] for c in payload["cycles"]}
        self.assertEqual(cycle_records[self.cycle.id], 10)
        self.assertEqual(cycle_records[second_cycle.id], 2)

    def test_column_summary_returns_typed_stats_and_unit_metadata(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}&column_names=gross_floor_area,extra_numeric"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["total_records"], 10)
        self.assertEqual(payload["selected_column_names"], ["gross_floor_area", "extra_numeric"])

        cycle_data = payload["cycles"][0]
        self.assertEqual(cycle_data["cycle_id"], self.cycle.id)
        self.assertEqual(cycle_data["total_records"], 10)

        by_name = {row["column_name"]: row for row in cycle_data["columns"]}
        gross_floor_area = by_name["gross_floor_area"]
        extra_numeric = by_name["extra_numeric"]

        self.assertEqual(gross_floor_area["data_type"], "area")
        self.assertEqual(gross_floor_area["db_type"], "float")
        self.assertEqual(gross_floor_area["stats"]["non_null_count"], 10)
        self.assertEqual(gross_floor_area["stats"]["null_count"], 0)
        self.assertEqual(gross_floor_area["stats"]["sum"], self.expected_total_sqft)
        self.assertIsNotNone(gross_floor_area["unit"]["display_unit_name"])
        self.assertIsNotNone(gross_floor_area["unit"]["display_unit_spec"])

        self.assertEqual(extra_numeric["data_type"], "float")
        self.assertEqual(extra_numeric["db_type"], "float")
        self.assertEqual(extra_numeric["stats"]["non_null_count"], 5)
        self.assertEqual(extra_numeric["stats"]["null_count"], 5)
        self.assertEqual(extra_numeric["stats"]["min"], 10.0)
        self.assertEqual(extra_numeric["stats"]["max"], 50.0)
        self.assertEqual(extra_numeric["stats"]["sum"], 150.0)
        self.assertEqual(extra_numeric["stats"]["distinct_count"], 5)
        self.assertEqual(extra_numeric["unit"]["unit_name"], "kBtu")
        self.assertEqual(extra_numeric["unit"]["units_pint"], "kBtu")
        self.assertEqual(extra_numeric["unit"]["unit_type_display"], "Float")
        self.assertEqual(extra_numeric["unit"]["display_unit_name"], "kBtu")

    def test_column_summary_requires_known_columns(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}&column_names=does_not_exist"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

        payload = response.json()
        self.assertEqual(payload["success"], False)
        self.assertEqual(payload["missing_columns"], ["does_not_exist"])

    def test_column_summary_can_include_raw_data_with_property_id(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}"
            + "&column_names=gross_floor_area,extra_numeric"
            + "&include_raw_data=true"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertTrue(payload["include_raw_data"])
        cycle_data = payload["cycles"][0]
        self.assertEqual(cycle_data["raw_data_count"], 10)
        self.assertEqual(len(cycle_data["raw_data"]["property_ids"]), 10)
        self.assertEqual(len(cycle_data["raw_data"]["property_state_ids"]), 10)
        self.assertEqual(len(cycle_data["raw_data"]["columns"]["gross_floor_area"]), 10)
        self.assertEqual(len(cycle_data["raw_data"]["columns"]["extra_numeric"]), 10)

        populated_extra_numeric = [value for value in cycle_data["raw_data"]["columns"]["extra_numeric"] if value is not None]
        self.assertEqual(len(populated_extra_numeric), 5)

    def test_column_summary_raw_data_limit(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}"
            + "&column_names=gross_floor_area"
            + "&include_raw_data=true"
            + "&raw_data_limit=3"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        cycle_data = payload["cycles"][0]
        self.assertEqual(cycle_data["raw_data_count"], 3)
        self.assertEqual(len(cycle_data["raw_data"]["property_ids"]), 3)
        self.assertEqual(len(cycle_data["raw_data"]["property_state_ids"]), 3)

    def test_column_summary_can_include_distribution_stats(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}"
            + "&column_names=extra_numeric"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        column = payload["cycles"][0]["columns"][0]
        stats = column["stats"]
        self.assertEqual(column["column_name"], "extra_numeric")
        self.assertEqual(stats["mode"], 10.0)
        self.assertEqual(stats["median"], 30.0)
        self.assertEqual(stats["p25"], 20.0)
        self.assertEqual(stats["p75"], 40.0)
        self.assertIsNotNone(stats["p05"])
        self.assertIsNotNone(stats["p95"])
        self.assertGreaterEqual(stats["p05"], stats["min"])
        self.assertLessEqual(stats["p05"], stats["p25"])
        self.assertGreaterEqual(stats["p95"], stats["p75"])
        self.assertLessEqual(stats["p95"], stats["max"])
        self.assertIsNotNone(stats["stddev"])

    def test_column_summary_returns_string_mode_for_string_columns(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}"
            + "&column_names=extra_field"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        column = payload["cycles"][0]["columns"][0]
        stats = column["stats"]

        self.assertEqual(column["column_name"], "extra_field")
        self.assertEqual(stats["mode"], "extra 0")
        self.assertEqual(stats["blank_count"], 0)
        self.assertEqual(stats["unique_count"], 5)
        self.assertEqual(stats["uniqueness_ratio"], 1.0)
        self.assertEqual(len(stats["top_k"]), 5)
        self.assertEqual(stats["top_k"][0], {"value": "extra 0", "count": 1})

    def test_column_summary_can_evaluate_all_columns(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary") + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}&column_names=all"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["include_raw_data"], False)
        self.assertGreater(len(payload["selected_column_names"]), 2)

        cycle_data = payload["cycles"][0]
        by_name = {row["column_name"]: row for row in cycle_data["columns"]}
        self.assertIn("gross_floor_area", by_name)
        self.assertIn("extra_field", by_name)

    def test_column_summary_disallows_raw_data_for_all_columns(self):
        url = (
            reverse_lazy("api:v4:properties-column-summary")
            + f"?organization_id={self.org.id}&cycle_ids={self.cycle.id}"
            + "&column_names=all"
            + "&include_raw_data=true"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertFalse(payload["success"])
        self.assertIn("column_names=all", payload["message"])
