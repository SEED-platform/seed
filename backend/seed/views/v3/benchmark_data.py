"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import csv
import json
from functools import lru_cache
from pathlib import Path

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm
from seed.utils.api import api_endpoint
from seed.utils.api_schema import AutoSchemaHelper

_DATA_DIR = Path(__file__).resolve().parent / "data"
_SITE_EUI_DATASETS = {
    "category": _DATA_DIR / "energystar_site_eui_by_category.csv",
    "subcategory": _DATA_DIR / "energystar_site_eui_by_subcategory.csv",
}
_FLOAT_FIELDS = {
    "fifth_percentile",
    "twenty_fifth_percentile",
    "median",
    "mean",
    "seventy_fifth_percentile",
    "ninety_fifth_percentile",
}
_INTEGER_FIELDS = {"year_reported"}


def _dataset_version(file_path: Path) -> int:
    return file_path.stat().st_mtime_ns


def _coerce_csv_row_types(row: dict[str, str]) -> dict[str, str | float | int | None]:
    typed_row: dict[str, str | float | int | None] = {}

    for key, value in row.items():
        if key in _FLOAT_FIELDS:
            typed_row[key] = float(value) if value else None
        elif key in _INTEGER_FIELDS:
            typed_row[key] = int(value) if value else None
        else:
            typed_row[key] = value

    return typed_row


@lru_cache(maxsize=len(_SITE_EUI_DATASETS))
def _cached_csv_content(file_path_str: str, version: int) -> str:
    del version
    return Path(file_path_str).read_text(encoding="utf-8")


@lru_cache(maxsize=len(_SITE_EUI_DATASETS))
def _cached_json_content(file_path_str: str, dataset: str, version: int) -> str:
    del version
    with Path(file_path_str).open(newline="", encoding="utf-8") as csv_file:
        rows = [_coerce_csv_row_types(row) for row in csv.DictReader(csv_file)]

    return json.dumps(
        {
            "status": "success",
            "dataset": dataset,
            "format": "json",
            "count": len(rows),
            "data": rows,
        }
    )


class BenchmarkDataViewSet(viewsets.ViewSet):
    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_enum_field(
                "dataset", "Benchmark dataset. Defaults to category", list(_SITE_EUI_DATASETS), required=False
            ),
            AutoSchemaHelper.query_enum_field("output_format", "Response format. Defaults to json", ["json", "csv"], required=False),
        ],
        responses={
            (200, "application/json"): AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "dataset": "string",
                    "format": "string",
                    "count": "integer",
                    "data": [
                        {
                            "building_type": "string",
                            "building_subtype": "string",
                            "climate_zone": "string",
                            "year_built": "string",
                            "weekly_hours": "string",
                            "gfa": "string",
                            "fifth_percentile": "number",
                            "twenty_fifth_percentile": "number",
                            "median": "number",
                            "mean": "number",
                            "seventy_fifth_percentile": "number",
                            "ninety_fifth_percentile": "number",
                            "climate_zone_description": "string",
                            "year_reported": "integer",
                            "row_count": "string",
                        }
                    ],
                },
                description=(
                    "Rows have `building_type` in the category dataset and `building_subtype` in the subcategory dataset. "
                    "Numeric values are null when blank."
                ),
            ),
            (200, "text/csv"): OpenApiTypes.BINARY,
        },
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"], url_path="site_eui")
    def site_eui(self, request):
        """Return site EUI benchmark data, defaulting to dataset=category and output_format=json."""
        dataset = str(request.query_params.get("dataset", "category")).strip().lower()
        output_format = str(request.query_params.get("output_format", "json")).strip().lower()

        if dataset not in _SITE_EUI_DATASETS:
            return {
                "status": "error",
                "message": "Invalid dataset. Expected one of: category, subcategory",
            }

        file_path = _SITE_EUI_DATASETS[dataset]
        if not file_path.exists():
            return HttpResponse(
                json.dumps({"status": "error", "message": f"Benchmark dataset file not found for '{dataset}'"}),
                content_type="application/json",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        dataset_version = _dataset_version(file_path)

        if output_format == "csv":
            content = _cached_csv_content(str(file_path), dataset_version)
            response = HttpResponse(content, content_type="text/csv; charset=utf-8", status=status.HTTP_200_OK)
            response["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
            return response

        if output_format != "json":
            return {
                "status": "error",
                "message": "Invalid format. Expected one of: json, csv",
            }

        content = _cached_json_content(str(file_path), dataset, dataset_version)
        return HttpResponse(content, content_type="application/json", status=status.HTTP_200_OK)
