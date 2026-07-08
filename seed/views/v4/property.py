"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
from datetime import date, datetime
from decimal import Decimal

from django.db import connection
from django.db.models import Avg, Count, Max, Min, Sum
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import Organization
from seed.models import AccessLevelInstance, Column, Cycle, PropertyState, PropertyView
from seed.models.columns import EXCLUDED_API_FIELDS
from seed.serializers.pint import DEFAULT_UNITS, pretty_units_from_spec
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper

NUMERIC_DATA_TYPES = {"number", "float", "integer", "area", "eui", "ghg", "ghg_intensity", "wui", "water_use"}
NON_STRING_DATA_TYPES = {"boolean", "date", "datetime", "geometry"}


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _parse_cycle_ids_only(cycle_ids: str | None) -> list[int] | None:
    if not cycle_ids:
        return None

    raw_values = [value.strip() for value in cycle_ids.split(",") if value.strip()]
    if not raw_values:
        return None

    try:
        parsed = [int(value) for value in raw_values]
    except ValueError:
        return []

    # Preserve request order while removing duplicates.
    return list(dict.fromkeys(parsed))


def _parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _serialize_stat_value(value, data_type: str):
    if value is None:
        return None

    if hasattr(value, "magnitude"):
        value = value.magnitude

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, bool):
        return bool(value)

    try:
        return Column.cast_column_value(data_type, value)
    except Exception:
        # Last-resort fallback for aggregates that don't map cleanly to parser inputs.
        if isinstance(value, Decimal):
            return float(value)
        return value


def _normalize_json_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return list(value)


def _safe_pretty_units(unit_spec: str | None) -> str | None:
    if not unit_spec:
        return None
    try:
        return pretty_units_from_spec(unit_spec)
    except Exception:
        return unit_spec


def _preferred_unit_spec_for_data_type(org, data_type: str) -> str | None:
    # Keep behavior aligned with SEED display unit preferences for pint-aware data types.
    if data_type == "area":
        return org.display_units_area or DEFAULT_UNITS.get("area")
    if data_type == "eui":
        return org.display_units_eui or DEFAULT_UNITS.get("eui")
    if data_type == "ghg":
        return org.display_units_ghg or DEFAULT_UNITS.get("ghg")
    if data_type == "ghg_intensity":
        return org.display_units_ghg_intensity or DEFAULT_UNITS.get("ghg_intensity")
    if data_type == "water_use":
        return org.display_units_water_use or DEFAULT_UNITS.get("water_use")
    if data_type == "wui":
        return org.display_units_wui or DEFAULT_UNITS.get("wui")
    return None


def _build_unit_metadata(column, org) -> dict:
    preferred_unit_spec = _preferred_unit_spec_for_data_type(org, column.data_type)
    raw_unit_spec = column.units_pint or preferred_unit_spec
    unit_name = column.unit.unit_name if column.unit else None
    unit_type = column.unit.unit_type if column.unit else None

    return {
        "unit_name": unit_name,
        "unit_type": unit_type,
        "unit_type_display": column.unit.get_unit_type_display() if column.unit else None,
        "units_pint": column.units_pint,
        "display_unit_spec": raw_unit_spec,
        "display_unit_name": _safe_pretty_units(raw_unit_spec),
    }


def _build_property_views_queryset(org_id: int, access_level_instance: AccessLevelInstance, selected_cycle_ids: list[int]):
    return PropertyView.objects.filter(
        property__organization_id=org_id,
        cycle_id__in=selected_cycle_ids,
        property__access_level_instance__lft__gte=access_level_instance.lft,
        property__access_level_instance__rgt__lte=access_level_instance.rgt,
    )


def _parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except ValueError:
        return -1
    return parsed


def _validate_cycles(org_id: int, selected_cycle_ids: list[int]) -> tuple[bool, JsonResponse | None]:
    existing_cycle_ids = set(Cycle.objects.filter(id__in=selected_cycle_ids, organization_id=org_id).values_list("id", flat=True))
    if len(existing_cycle_ids) != len(selected_cycle_ids):
        return False, JsonResponse({"success": False, "message": "One or more cycles do not exist"}, status=status.HTTP_404_NOT_FOUND)
    return True, None


def _get_columns(org_id: int, selected_column_names: list[str] | None = None):
    columns_qs = Column.objects.filter(organization_id=org_id, derived_column=None, table_name="PropertyState").exclude(
        column_name__in=EXCLUDED_API_FIELDS
    )
    if selected_column_names:
        columns_qs = columns_qs.filter(column_name__in=selected_column_names)
    return list(
        columns_qs.select_related("unit").only(
            "column_name", "display_name", "is_extra_data", "data_type", "units_pint", "unit__unit_name", "unit__unit_type"
        )
    )


def _compute_extra_data_stats(state_ids: list[int], extra_columns: list[Column]) -> dict[str, dict]:
    if not state_ids or not extra_columns:
        return {}

    column_names = [c.column_name for c in extra_columns]
    regex = r"^-?\d+(\.\d+)?$"

    query = """
        SELECT
            each_entry.key,
            COUNT(*) FILTER (WHERE each_entry.value IS NOT NULL AND each_entry.value <> '') AS non_null_count,
            COUNT(DISTINCT each_entry.value) FILTER (WHERE each_entry.value IS NOT NULL AND each_entry.value <> '') AS distinct_count,
            MIN((each_entry.value)::double precision) FILTER (WHERE each_entry.value ~ %s) AS min_num,
            MAX((each_entry.value)::double precision) FILTER (WHERE each_entry.value ~ %s) AS max_num,
            AVG((each_entry.value)::double precision) FILTER (WHERE each_entry.value ~ %s) AS avg_num,
            SUM((each_entry.value)::double precision) FILTER (WHERE each_entry.value ~ %s) AS sum_num
        FROM seed_propertystate ps
        JOIN LATERAL JSONB_EACH_TEXT(ps.extra_data) AS each_entry(key, value) ON TRUE
        WHERE ps.id = ANY(%s)
          AND each_entry.key = ANY(%s)
        GROUP BY each_entry.key
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [regex, regex, regex, regex, state_ids, column_names])
        rows = cursor.fetchall()

    stats_by_name = {}
    for key, non_null_count, distinct_count, min_num, max_num, avg_num, sum_num in rows:
        stats_by_name[key] = {
            "non_null_count": int(non_null_count or 0),
            "distinct_count": int(distinct_count or 0),
            "min": float(min_num) if min_num is not None else None,
            "max": float(max_num) if max_num is not None else None,
            "avg": float(avg_num) if avg_num is not None else None,
            "sum": float(sum_num) if sum_num is not None else None,
        }
    return stats_by_name


def _compute_extra_data_distribution_stats(state_ids: list[int], extra_columns: list[Column]) -> dict[str, dict]:
    if not state_ids or not extra_columns:
        return {}

    numeric_column_names = [c.column_name for c in extra_columns if c.data_type in NUMERIC_DATA_TYPES]
    if not numeric_column_names:
        return {}

    regex = r"^-?\d+(\.\d+)?$"
    query = """
        WITH numeric_values AS (
            SELECT
                each_entry.key AS key,
                (each_entry.value)::double precision AS value
            FROM seed_propertystate ps
            JOIN LATERAL JSONB_EACH_TEXT(ps.extra_data) AS each_entry(key, value) ON TRUE
            WHERE ps.id = ANY(%s)
              AND each_entry.key = ANY(%s)
              AND each_entry.value ~ %s
        ),
        mode_values AS (
            SELECT
                key,
                value,
                ROW_NUMBER() OVER (PARTITION BY key ORDER BY COUNT(*) DESC, value ASC) AS rn
            FROM numeric_values
            GROUP BY key, value
        )
        SELECT
            nv.key,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY nv.value) AS median,
            percentile_cont(0.05) WITHIN GROUP (ORDER BY nv.value) AS p05,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY nv.value) AS p25,
            percentile_cont(0.75) WITHIN GROUP (ORDER BY nv.value) AS p75,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY nv.value) AS p95,
            stddev_pop(nv.value) AS stddev,
            MAX(CASE WHEN mv.rn = 1 THEN mv.value END) AS mode
        FROM numeric_values nv
        LEFT JOIN mode_values mv ON mv.key = nv.key
        GROUP BY nv.key
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [state_ids, numeric_column_names, regex])
        rows = cursor.fetchall()

    distribution_by_name = {}
    for key, median, p05, p25, p75, p95, stddev, mode in rows:
        distribution_by_name[key] = {
            "median": float(median) if median is not None else None,
            "p05": float(p05) if p05 is not None else None,
            "p25": float(p25) if p25 is not None else None,
            "p75": float(p75) if p75 is not None else None,
            "p95": float(p95) if p95 is not None else None,
            "stddev": float(stddev) if stddev is not None else None,
            "mode": float(mode) if mode is not None else None,
        }

    return distribution_by_name


def _is_string_like_data_type(data_type: str | None) -> bool:
    if not data_type or data_type == "None":
        return True
    return data_type not in NUMERIC_DATA_TYPES and data_type not in NON_STRING_DATA_TYPES


def _compute_extra_data_string_stats(state_ids: list[int], extra_columns: list[Column], top_k_limit: int = 5) -> dict[str, dict]:
    if not state_ids or not extra_columns:
        return {}

    string_column_names = [c.column_name for c in extra_columns if _is_string_like_data_type(c.data_type)]
    if not string_column_names:
        return {}

    query = """
        WITH grouped AS (
            SELECT
                each_entry.key,
                each_entry.value,
                COUNT(*) AS value_count
            FROM seed_propertystate ps
            JOIN LATERAL JSONB_EACH_TEXT(ps.extra_data) AS each_entry(key, value) ON TRUE
            WHERE ps.id = ANY(%s)
              AND each_entry.key = ANY(%s)
              AND each_entry.value IS NOT NULL
            GROUP BY each_entry.key, each_entry.value
        ), ranked_nonblank AS (
            SELECT
                key,
                value,
                value_count,
                ROW_NUMBER() OVER (PARTITION BY key ORDER BY value_count DESC, value ASC) AS rn
            FROM grouped
            WHERE value <> ''
        ), summary AS (
            SELECT
                key,
                COALESCE(COUNT(*) FILTER (WHERE value_count = 1 AND value <> ''), 0) AS unique_count,
                COALESCE(SUM(value_count) FILTER (WHERE value = ''), 0) AS blank_count
            FROM grouped
            GROUP BY key
        ), top_k_agg AS (
            SELECT
                key,
                COALESCE(
                    jsonb_agg(jsonb_build_object('value', value, 'count', value_count) ORDER BY value_count DESC, value ASC),
                    '[]'::jsonb
                ) AS top_k
            FROM ranked_nonblank
            WHERE rn <= %s
            GROUP BY key
        )
        SELECT
            s.key,
            MAX(r.value) FILTER (WHERE r.rn = 1) AS mode,
            s.unique_count,
            s.blank_count,
            COALESCE(t.top_k, '[]'::jsonb) AS top_k
        FROM summary s
        LEFT JOIN ranked_nonblank r ON r.key = s.key
        LEFT JOIN top_k_agg t ON t.key = s.key
        GROUP BY s.key, s.unique_count, s.blank_count, t.top_k
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [state_ids, string_column_names, top_k_limit])
        rows = cursor.fetchall()

    return {
        key: {
            "mode": mode,
            "unique_count": int(unique_count or 0),
            "blank_count": int(blank_count or 0),
            "top_k": _normalize_json_list(top_k),
        }
        for key, mode, unique_count, blank_count, top_k in rows
    }


def _compute_canonical_string_stats(state_ids: list[int], canonical_columns: list[Column], top_k_limit: int = 5) -> dict[str, dict]:
    if not state_ids or not canonical_columns:
        return {}

    string_columns = [c for c in canonical_columns if _is_string_like_data_type(c.data_type)]
    if not string_columns:
        return {}

    string_column_names = [column.column_name for column in string_columns]
    query = """
        WITH grouped AS (
            SELECT
                each_entry.key,
                each_entry.value,
                COUNT(*) AS value_count
            FROM seed_propertystate ps
            JOIN LATERAL JSONB_EACH_TEXT(to_jsonb(ps)) AS each_entry(key, value) ON TRUE
            WHERE ps.id = ANY(%s)
              AND each_entry.key = ANY(%s)
              AND each_entry.value IS NOT NULL
            GROUP BY each_entry.key, each_entry.value
        ), ranked_nonblank AS (
            SELECT
                key,
                value,
                value_count,
                ROW_NUMBER() OVER (PARTITION BY key ORDER BY value_count DESC, value ASC) AS rn
            FROM grouped
            WHERE value <> ''
        ), summary AS (
            SELECT
                key,
                COALESCE(COUNT(*) FILTER (WHERE value_count = 1 AND value <> ''), 0) AS unique_count,
                COALESCE(SUM(value_count) FILTER (WHERE value = ''), 0) AS blank_count
            FROM grouped
            GROUP BY key
        ), top_k_agg AS (
            SELECT
                key,
                COALESCE(
                    jsonb_agg(jsonb_build_object('value', value, 'count', value_count) ORDER BY value_count DESC, value ASC),
                    '[]'::jsonb
                ) AS top_k
            FROM ranked_nonblank
            WHERE rn <= %s
            GROUP BY key
        )
        SELECT
            s.key,
            MAX(r.value) FILTER (WHERE r.rn = 1) AS mode,
            s.unique_count,
            s.blank_count,
            COALESCE(t.top_k, '[]'::jsonb) AS top_k
        FROM summary s
        LEFT JOIN ranked_nonblank r ON r.key = s.key
        LEFT JOIN top_k_agg t ON t.key = s.key
        GROUP BY s.key, s.unique_count, s.blank_count, t.top_k
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [state_ids, string_column_names, top_k_limit])
        rows = cursor.fetchall()

    return {
        key: {
            "mode": mode,
            "unique_count": int(unique_count or 0),
            "blank_count": int(blank_count or 0),
            "top_k": _normalize_json_list(top_k),
        }
        for key, mode, unique_count, blank_count, top_k in rows
    }


def _build_column_summary_for_state_ids(state_ids: list[int], selected_column_names: list[str], columns: list[Column], org) -> list[dict]:
    by_name = {c.column_name: c for c in columns}
    canonical_columns = [c for c in columns if not c.is_extra_data]
    extra_columns = [c for c in columns if c.is_extra_data]

    aggregate_kwargs = {}
    column_aliases = {}
    for i, column in enumerate(canonical_columns):
        alias = f"c{i}"
        column_aliases[column.column_name] = alias
        field_name = column.column_name
        aggregate_kwargs[f"{alias}_non_null"] = Count(field_name)
        aggregate_kwargs[f"{alias}_distinct"] = Count(field_name, distinct=True)
        if column.data_type in NUMERIC_DATA_TYPES:
            aggregate_kwargs[f"{alias}_min"] = Min(field_name)
            aggregate_kwargs[f"{alias}_max"] = Max(field_name)
            aggregate_kwargs[f"{alias}_avg"] = Avg(field_name)
            aggregate_kwargs[f"{alias}_sum"] = Sum(field_name)

    canonical_aggregates = PropertyState.objects.filter(id__in=state_ids).aggregate(**aggregate_kwargs) if aggregate_kwargs else {}
    extra_stats_by_name = _compute_extra_data_stats(state_ids, extra_columns)
    extra_distribution_by_name = _compute_extra_data_distribution_stats(state_ids, extra_columns)
    extra_string_stats_by_name = _compute_extra_data_string_stats(state_ids, extra_columns)
    canonical_string_stats_by_name = _compute_canonical_string_stats(state_ids, canonical_columns)

    canonical_distribution_by_name = {}
    if canonical_columns:
        numeric_column_names = [column.column_name for column in canonical_columns if column.data_type in NUMERIC_DATA_TYPES]

        if numeric_column_names:
            regex = r"^-?\d+(\.\d+)?$"
            query = """
                WITH numeric_values AS (
                    SELECT
                        each_entry.key,
                        (each_entry.value)::double precision AS value
                    FROM seed_propertystate ps
                    JOIN LATERAL JSONB_EACH_TEXT(to_jsonb(ps)) AS each_entry(key, value) ON TRUE
                    WHERE ps.id = ANY(%s)
                      AND each_entry.key = ANY(%s)
                      AND each_entry.value ~ %s
                ),
                mode_values AS (
                    SELECT
                        key,
                        value,
                        ROW_NUMBER() OVER (PARTITION BY key ORDER BY COUNT(*) DESC, value ASC) AS rn
                    FROM numeric_values
                    GROUP BY key, value
                )
                SELECT
                    nv.key,
                    percentile_cont(0.5) WITHIN GROUP (ORDER BY nv.value) AS median,
                    percentile_cont(0.05) WITHIN GROUP (ORDER BY nv.value) AS p05,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY nv.value) AS p25,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY nv.value) AS p75,
                    percentile_cont(0.95) WITHIN GROUP (ORDER BY nv.value) AS p95,
                    stddev_pop(nv.value) AS stddev,
                    MAX(CASE WHEN mv.rn = 1 THEN mv.value END) AS mode
                FROM numeric_values nv
                LEFT JOIN mode_values mv ON mv.key = nv.key
                GROUP BY nv.key
            """
            with connection.cursor() as cursor:
                cursor.execute(query, [state_ids, numeric_column_names, regex])
                rows = cursor.fetchall()

            for key, median, p05, p25, p75, p95, stddev, mode in rows:
                canonical_distribution_by_name[key] = {
                    "median": float(median) if median is not None else None,
                    "p05": float(p05) if p05 is not None else None,
                    "p25": float(p25) if p25 is not None else None,
                    "p75": float(p75) if p75 is not None else None,
                    "p95": float(p95) if p95 is not None else None,
                    "stddev": float(stddev) if stddev is not None else None,
                    "mode": float(mode) if mode is not None else None,
                }

    total_records = len(state_ids)
    results = []
    for name in selected_column_names:
        column = by_name[name]
        data_type = column.data_type
        if column.is_extra_data:
            extra_stats = extra_stats_by_name.get(
                column.column_name,
                {
                    "non_null_count": 0,
                    "distinct_count": 0,
                    "min": None,
                    "max": None,
                    "avg": None,
                    "sum": None,
                },
            )
            non_null_count = extra_stats["non_null_count"]
            distinct_count = extra_stats["distinct_count"]
            min_value = extra_stats["min"] if data_type in NUMERIC_DATA_TYPES else None
            max_value = extra_stats["max"] if data_type in NUMERIC_DATA_TYPES else None
            avg_value = extra_stats["avg"] if data_type in NUMERIC_DATA_TYPES else None
            sum_value = extra_stats["sum"] if data_type in NUMERIC_DATA_TYPES else None
            distribution_values = extra_distribution_by_name.get(column.column_name, {})
            string_values = extra_string_stats_by_name.get(column.column_name, {})
        else:
            alias = column_aliases[column.column_name]
            non_null_count = int(canonical_aggregates.get(f"{alias}_non_null") or 0)
            distinct_count = int(canonical_aggregates.get(f"{alias}_distinct") or 0)
            min_value = _serialize_stat_value(canonical_aggregates.get(f"{alias}_min"), data_type)
            max_value = _serialize_stat_value(canonical_aggregates.get(f"{alias}_max"), data_type)
            avg_value = _serialize_stat_value(canonical_aggregates.get(f"{alias}_avg"), data_type)
            sum_value = _serialize_stat_value(canonical_aggregates.get(f"{alias}_sum"), data_type)
            distribution_values = canonical_distribution_by_name.get(column.column_name, {})
            string_values = canonical_string_stats_by_name.get(column.column_name, {})
            if data_type not in NUMERIC_DATA_TYPES:
                min_value = None
                max_value = None
                avg_value = None
                sum_value = None
                distribution_values = {}

        uniqueness_ratio = None
        if string_values:
            uniqueness_ratio = (string_values.get("unique_count") / non_null_count) if non_null_count else None

        results.append(
            {
                "column_name": column.column_name,
                "display_name": column.display_name or column.column_name.replace("_", " "),
                "is_extra_data": column.is_extra_data,
                "data_type": data_type,
                "db_type": Column.DB_TYPES.get(data_type, data_type),
                "unit": {
                    **_build_unit_metadata(column, org),
                },
                "stats": {
                    "non_null_count": non_null_count,
                    "null_count": total_records - non_null_count,
                    "distinct_count": distinct_count,
                    "min": min_value,
                    "max": max_value,
                    "avg": avg_value,
                    "sum": sum_value,
                    "median": distribution_values.get("median"),
                    "p05": distribution_values.get("p05"),
                    "p25": distribution_values.get("p25"),
                    "p75": distribution_values.get("p75"),
                    "p95": distribution_values.get("p95"),
                    "stddev": distribution_values.get("stddev"),
                    "mode": (distribution_values.get("mode") if data_type in NUMERIC_DATA_TYPES else string_values.get("mode")),
                    "top_k": string_values.get("top_k"),
                    "unique_count": string_values.get("unique_count"),
                    "uniqueness_ratio": uniqueness_ratio,
                    "blank_count": string_values.get("blank_count"),
                },
            }
        )

    return results


class PropertyViewSet(viewsets.ViewSet, OrgMixin):
    pagination_class = None

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_string_field(
                "cycle_ids",
                required=True,
                description="Required comma-separated cycle IDs. Single-cycle requests should pass one ID.",
            ),
            AutoSchemaHelper.query_string_field(
                "column_names",
                required=True,
                description="Required comma-separated property column names to summarize, or 'all' to evaluate all property columns",
            ),
            AutoSchemaHelper.query_boolean_field(
                "include_raw_data",
                required=False,
                description="If true, include row-level selected column values keyed by property_id",
            ),
            AutoSchemaHelper.query_integer_field(
                "raw_data_limit",
                required=False,
                description="Optional max number of raw rows to return when include_raw_data=true",
            ),
        ]
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def column_summary(self, request):
        """Fast typed per-cycle summary stats for selected property columns with unit metadata."""
        org_id = self.get_organization(request)
        cycle_ids = request.query_params.get("cycle_ids")
        include_raw_data = _parse_bool(request.query_params.get("include_raw_data"), default=False)
        raw_data_limit = _parse_int(request.query_params.get("raw_data_limit"))
        requested_column_names = _parse_csv(request.query_params.get("column_names"))
        org = Organization.objects.get(pk=org_id)

        if raw_data_limit is not None and raw_data_limit < 1:
            return JsonResponse(
                {"success": False, "message": "raw_data_limit must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not requested_column_names:
            return JsonResponse({"success": False, "message": "column_names parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        all_columns_requested = len(requested_column_names) == 1 and requested_column_names[0].lower() == "all"
        if all_columns_requested and include_raw_data:
            return JsonResponse(
                {"success": False, "message": "include_raw_data cannot be true when column_names=all"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        selected_cycle_ids = _parse_cycle_ids_only(cycle_ids)
        if selected_cycle_ids is None:
            return JsonResponse({"success": False, "message": "cycle_ids parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not selected_cycle_ids:
            return JsonResponse({"success": False, "message": "cycle_ids must be valid integers"}, status=status.HTTP_400_BAD_REQUEST)

        is_valid, error_response = _validate_cycles(org_id, selected_cycle_ids)
        if not is_valid:
            return error_response

        columns = _get_columns(org_id, None if all_columns_requested else requested_column_names)
        selected_column_names = [c.column_name for c in columns] if all_columns_requested else requested_column_names
        by_name = {c.column_name: c for c in columns}
        missing_columns = [] if all_columns_requested else [name for name in requested_column_names if name not in by_name]
        if missing_columns:
            return JsonResponse(
                {"success": False, "message": "One or more columns do not exist", "missing_columns": missing_columns},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cycle_summaries = []
        any_records = False
        total_records = 0
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        for selected_cycle_id in selected_cycle_ids:
            property_views_qs = _build_property_views_queryset(org_id, access_level_instance, [selected_cycle_id])
            state_ids = list(property_views_qs.values_list("state_id", flat=True))
            cycle_total_records = len(state_ids)
            total_records += cycle_total_records
            if cycle_total_records > 0:
                any_records = True

            cycle_summary = {
                "cycle_id": selected_cycle_id,
                "total_records": cycle_total_records,
                "columns": _build_column_summary_for_state_ids(state_ids, selected_column_names, columns, org)
                if cycle_total_records > 0
                else [],
            }

            if include_raw_data:
                canonical_columns = [c for c in columns if not c.is_extra_data]
                canonical_projection = [f"state__{c.column_name}" for c in canonical_columns]
                raw_qs = property_views_qs.order_by("property_id", "id").values(
                    "property_id", "state_id", "state__extra_data", *canonical_projection
                )
                if raw_data_limit is not None:
                    raw_qs = raw_qs[:raw_data_limit]

                raw_rows = list(raw_qs)
                raw_columns = {column_name: [] for column_name in selected_column_names}
                property_ids = []
                property_state_ids = []

                for row in raw_rows:
                    extra_data = row.get("state__extra_data") or {}
                    property_ids.append(row["property_id"])
                    property_state_ids.append(row["state_id"])

                    for column_name in selected_column_names:
                        column = by_name[column_name]
                        if column.is_extra_data:
                            raw_value = extra_data.get(column_name)
                        else:
                            raw_value = row.get(f"state__{column_name}")
                        raw_columns[column_name].append(_serialize_stat_value(raw_value, column.data_type))

                cycle_summary["raw_data"] = {
                    "property_ids": property_ids,
                    "property_state_ids": property_state_ids,
                    "columns": raw_columns,
                }
                cycle_summary["raw_data_count"] = len(property_ids)

            cycle_summaries.append(cycle_summary)

        if not any_records:
            return JsonResponse(
                {"success": False, "message": "No properties found for the given cycle selection"}, status=status.HTTP_404_NOT_FOUND
            )

        response = {
            "status": "success",
            "selected_cycle_ids": selected_cycle_ids,
            "selected_column_names": selected_column_names,
            "total_records": total_records,
            "include_raw_data": include_raw_data,
            "cycles": cycle_summaries,
        }

        return JsonResponse(response)
