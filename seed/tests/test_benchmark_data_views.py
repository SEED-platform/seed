"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.urls import reverse_lazy

from seed.tests.util import AccessLevelBaseTestCase


class TestBenchmarkDataViews(AccessLevelBaseTestCase):
    def test_site_eui_benchmark_data_json(self):
        url = reverse_lazy("api:v3:benchmark_data-site-eui") + f"?organization_id={self.org.id}&dataset=category&output_format=json"

        response = self.client.get(url, content_type="application/json")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["dataset"] == "category"
        assert body["format"] == "json"
        assert body["count"] > 0
        assert body["data"][0]["building_type"] == "All"
        assert isinstance(body["data"][0]["fifth_percentile"], float)
        assert isinstance(body["data"][0]["median"], float)
        assert isinstance(body["data"][0]["mean"], float)
        assert isinstance(body["data"][0]["year_reported"], int)

    def test_site_eui_benchmark_data_json_uses_null_for_blank_numeric_fields(self):
        url = reverse_lazy("api:v3:benchmark_data-site-eui") + f"?organization_id={self.org.id}&dataset=category&output_format=json"

        response = self.client.get(url, content_type="application/json")

        assert response.status_code == 200
        rows = response.json()["data"]
        row_with_blanks = next(
            row
            for row in rows
            if all(
                row[field] is None
                for field in (
                    "fifth_percentile",
                    "twenty_fifth_percentile",
                    "median",
                    "mean",
                    "seventy_fifth_percentile",
                    "ninety_fifth_percentile",
                )
            )
        )
        assert row_with_blanks["fifth_percentile"] is None
        assert row_with_blanks["twenty_fifth_percentile"] is None
        assert row_with_blanks["median"] is None
        assert row_with_blanks["mean"] is None
        assert row_with_blanks["seventy_fifth_percentile"] is None
        assert row_with_blanks["ninety_fifth_percentile"] is None
        assert isinstance(row_with_blanks["year_reported"], int)

    def test_site_eui_benchmark_data_csv(self):
        url = reverse_lazy("api:v3:benchmark_data-site-eui") + f"?organization_id={self.org.id}&dataset=subcategory&output_format=csv"

        response = self.client.get(url, content_type="application/json")

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        assert "building_subtype,climate_zone" in response.content.decode("utf-8")

    def test_site_eui_benchmark_data_rejects_invalid_dataset(self):
        url = reverse_lazy("api:v3:benchmark_data-site-eui") + f"?organization_id={self.org.id}&dataset=foo&output_format=json"

        response = self.client.get(url, content_type="application/json")

        assert response.status_code == 400
        body = response.json()
        assert body["status"] == "error"
        assert "Invalid dataset" in body["message"]
