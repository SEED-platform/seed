"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re
from datetime import UTC, date, datetime
from functools import reduce
from operator import and_, or_

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Case, Exists, F, FloatField, Func, OuterRef, Q, TextField, Value, When
from django.db.models.functions import Abs, Cast, Floor, Left, Replace, Round, Sign, TruncDate
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    IContains,
    IEndsWith,
    IExact,
    IsNull,
    IStartsWith,
    LessThan,
    LessThanOrEqual,
    Regex,
)
from django.db.utils import DataError
from django.http import JsonResponse, QueryDict
from django.utils.timezone import get_current_timezone
from quantityfield.units import ureg
from rest_framework import status

from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models import (
    VIEW_LIST,
    VIEW_LIST_PROPERTY,
    VIEW_LIST_TAXLOT,
    Column,
    ColumnListProfile,
    ColumnListProfileColumn,
    Cycle,
    PropertyView,
    TaxLotProperty,
    TaxLotView,
)
from seed.serializers.column_list_profiles import ColumnListProfileSerializer
from seed.serializers.columns import ColumnSerializer
from seed.serializers.pint import DEFAULT_UNITS, apply_display_unit_preferences, display_units
from seed.utils.search import FilterError, build_view_filters_and_sorts

# The conditions AG Grid's text, number, and date filters send
TEXT_CONDITIONS = {"contains", "notContains", "equals", "notEqual", "startsWith", "endsWith", "blank", "notBlank"}
COMPARISONS = {
    "equals": Exact,
    "greaterThan": GreaterThan,
    "greaterThanOrEqual": GreaterThanOrEqual,
    "lessThan": LessThan,
    "lessThanOrEqual": LessThanOrEqual,
}
COMPARISON_CONDITIONS = {*COMPARISONS, "notEqual", "inRange", "blank", "notBlank"}
FILTER_CONDITIONS = {"text": TEXT_CONDITIONS, "number": COMPARISON_CONDITIONS, "date": COMPARISON_CONDITIONS}
TEXT_LOOKUPS = {"contains": IContains, "equals": IExact, "startsWith": IStartsWith, "endsWith": IEndsWith}
# The keys of each filter type's values (from and to), most expected first
VALUE_KEYS = {
    "text": (("filter",), ()),
    "number": (("filter",), ("filterTo",)),
    "date": (("dateFrom", "filter"), ("dateTo", "filterTo")),
}
NEGATED_TEXT_CONDITIONS = {"notContains": "contains", "notEqual": "equals"}

NUMBER_FIELD_TYPES = {"IntegerField", "BigIntegerField", "SmallIntegerField", "PositiveIntegerField", "FloatField", "DecimalField"}
STRING_FIELD_TYPES = {None, "CharField", "TextField"}  # None for JSON values (extra data and derived columns)
# Text that is a number, possibly with thousands separators removed, or that starts with a date
NUMBER_PATTERN = r"^\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?\s*$"
DATE_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"


def json_text(json_field, key):
    """A JSON object's value for `key` as text, or null if it's missing or null (`->>` would read numeric keys as indexes)"""
    return Func(json_field, Value(key), function="jsonb_extract_path_text", output_field=TextField())


def round_half_even(number, places):
    """
    A float rounded as Python's `round` does (see `collapse_unit`): half to even, of its exact binary value. Django's
    `Round` rounds a numeric cast instead, half away from zero. PostgreSQL's `round(double precision)` rounds half to even,
    but of `number * 10^places`, which can round to a half itself (2.675 * 100 is 267.5, but 2.675 is 2.67499...), so a
    half moves toward the product's exact value, by the sign of its rounding error (Dekker's product, splitting `number`;
    10^places needs no split for places up to 11). Exact for places up to 11.
    """
    number = Cast(number, FloatField())  # not numeric, e.g., from a literal
    if places > 11:
        return Round(number, places)
    scale = Value(float(10**places))
    scaled = number * scale
    split = number * Value(2.0**27 + 1)
    high = split - (split - number)
    error = (high * scale - scaled) + (number - high) * scale
    # An exact half (`scaled - Floor(scaled)` can round to one, e.g., for -0.49999999999999994)
    half = Exact(scaled, Floor(scaled) + Value(0.5))
    nudge = Case(When(half, then=Sign(error) * Value(0.5)), default=Value(0.0))
    rounded = Func(scaled + nudge, function="ROUND", output_field=FloatField()) / scale
    # Python's `round` leaves larger numbers as they are, and their error terms could overflow
    return Case(When(GreaterThanOrEqual(Abs(number), Value(2**53 / 10**places)), then=number), default=rounded)


class InventoryFilterError(Exception):
    """Custom exception for inventory filter errors"""

    def __init__(self, response: JsonResponse):
        self.response = response


class InventoryFilter:
    """
    Filters and sorts inventory for the grid, which leaves all filtering to the server. Filters compare what the grid
    shows: text case-insensitively, numbers in the organization's display units and rounding, and dates by day.
    Blank is null or empty for every filter. Related columns match if any related record does, and their negated
    conditions if none does.
    """

    def __init__(self, request, profile_id=None):
        self.request = request
        self.profile_id = profile_id
        # class vars to be set through get_filtered_results
        self.access_level_instance = None
        self.columns_by_name = None
        self.cycle = None
        self.db_columns = None
        self.ids_only = None
        self.include_related = None
        self.inventory_type = None
        self.page = None
        self.paginator = None
        self.per_page = None
        self.org = None
        self.shown_column_ids = None

    @classmethod
    def filter_model_to_q(cls, filter_model, columns, inventory_type, access_level_names, organization=None):
        """
        A Q object for an AG Grid filter model, without a request (e.g., for a filter group the grid saved).
        Raises FilterError for invalid filters.

        :param filter_model: filters keyed by column name (`{column_name}_{id}`) or access level name
        :param columns: `Column.retrieve_all` columns, including related ones to filter by them
        :param access_level_names: the organization's access level names, including the root's
        :param organization: the organization whose display units number filters use (base units without one)
        """
        inventory_filter = cls(request=None)
        inventory_filter.org = organization
        inventory_filter.columns_by_name = {c["name"]: c for c in columns}
        inventory_filter.inventory_type = inventory_type
        inventory_filter.ali_level_names = set((access_level_names or [])[1:])
        return inventory_filter.generate_q_filters(filter_model)

    @classmethod
    def filters_to_q(cls, filters, columns, inventory_type, access_level_names, organization=None):
        """
        A Q object and the annotations it needs for filters that can mix the grid's AG Grid filter models (dict values
        keyed by `{column_name}_{id}` or access level name) and legacy filters (`{column_name}_{id}__{lookup}` keys,
        e.g., in filter groups the legacy UI saved), on this or the related inventory type's columns. Raises FilterError
        for invalid filters.
        """
        if not filters:
            return Q(), {}
        if not isinstance(filters, dict):
            raise FilterError("Invalid filters")

        legacy_filters = QueryDict(mutable=True)
        legacy_filters.update({k: v for k, v in filters.items() if not isinstance(v, dict)})
        q, annotations, _ = build_view_filters_and_sorts(legacy_filters, columns, inventory_type, access_level_names, include_sorts=False)
        q &= cls.legacy_related_q(legacy_filters, columns, inventory_type)
        filter_models = {k: v for k, v in filters.items() if isinstance(v, dict)}
        return q & cls.filter_model_to_q(filter_models, columns, inventory_type, access_level_names, organization), annotations

    @staticmethod
    def legacy_related_q(legacy_filters, columns, inventory_type):
        """
        A Q object for legacy filters on related columns, which `build_view_filters_and_sorts` ignores. As in the v3 API,
        they match views with a related record that matches them all, and, if one is for blanks (`__exact` ""), views
        without related records
        """
        other_type = "property" if inventory_type == "taxlot" else "taxlot"
        # The other inventory type's columns, to which this type's are related
        other_columns = [{**c, "related": not c["related"]} for c in columns]
        q, annotations, _ = build_view_filters_and_sorts(legacy_filters, other_columns, other_type, include_sorts=False)
        if not q:
            return Q()

        # Annotate the related views only, as their aliases can be this type's too (e.g., for extra data of the same name)
        other_views = PropertyView.objects if other_type == "property" else TaxLotView.objects
        try:
            related = other_views.annotate(**annotations).filter(q, **{f"taxlotproperty__{inventory_type}_view": OuterRef("pk")})
        except (ValueError, ValidationError) as e:
            raise FilterError(f"Error filtering - your data might not match the column settings data type: {e!s}") from e
        matches = Q(Exists(related))

        related_names = {c["name"] for c in columns if c["related"]}
        if any(k.endswith("__exact") and v == "" and k.split("__")[0] in related_names for k, v in legacy_filters.items()):
            matches |= ~Q(Exists(TaxLotProperty.objects.filter(**{f"{inventory_type}_view": OuterRef("pk")})))
        return matches

    def get_filtered_results(self):
        """Main method to get the filtered results"""
        try:
            self.validate_request()
            views_qs = self.get_views_list()
            views_qs = self.ag_filter_sort_views_list(views_qs)
            views_qs = self.include_exclude_views_list(views_qs)
            if self.ids_only:
                return self.get_id_list(views_qs)
            views_paginated = self.get_paginator(views_qs)
            show_columns = self.get_show_columns()
            related_results = self.serialize_views(views_paginated, show_columns)

        except InventoryFilterError as e:
            return e.response

        unit_collapsed_results = [apply_display_unit_preferences(self.org, x) for x in related_results]
        results = self.parse_related_results(unit_collapsed_results)
        column_defs = self.get_column_defs()
        response = self.build_response(results, column_defs)

        return JsonResponse(response)

    def validate_request(self):
        """validates request, assigns class variables"""
        page = self.request.query_params.get("page", 1)
        per_page = self.request.query_params.get("per_page", 100)
        org_id = self.request.query_params.get("organization_id")
        cycle_id = self.request.query_params.get("cycle")
        inventory_type = self.request.query_params.get("inventory_type")
        ids_only = self.request.query_params.get("ids_only", "false").lower() == "true"
        if profile_id := self.request.query_params.get("profile_id"):
            try:
                self.profile_id = int(profile_id)
            except ValueError as e:
                raise InventoryFilterError(
                    JsonResponse({"status": "error", "message": "profile_id must be an integer"}, status=status.HTTP_400_BAD_REQUEST)
                ) from e
        shown_column_ids = self.request.query_params.get("shown_column_ids")

        if not org_id:
            raise InventoryFilterError(
                JsonResponse(
                    {"status": "error", "message": "Need to pass organization_id as query parameter"}, status=status.HTTP_400_BAD_REQUEST
                )
            )
        org = Organization.objects.get(id=org_id)

        access_level_instance_id = self.request.data.get("access_level_instance_id", self.request.access_level_instance_id)
        access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
        user_ali = AccessLevelInstance.objects.get(id=self.request.access_level_instance_id)
        if not (user_ali == access_level_instance or access_level_instance.is_descendant_of(user_ali)):
            raise InventoryFilterError(
                JsonResponse(
                    {"status": "error", "message": f"No access_level_instance with id {access_level_instance_id}."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            )

        if cycle_id:
            try:
                cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
            except (Cycle.DoesNotExist, ValueError) as e:
                raise InventoryFilterError(
                    JsonResponse({"status": "error", "message": "No such cycle."}, status=status.HTTP_404_NOT_FOUND)
                ) from e
        else:
            cycle = Cycle.objects.filter(organization_id=org_id).order_by("name")
            if cycle:
                cycle = cycle.first()
        if not cycle:
            raise InventoryFilterError(
                JsonResponse(
                    {"status": "error", "message": "Could not locate cycle", "pagination": {"total": 0}, "cycle_id": None, "results": []}
                )
            )

        include_related = str(self.request.query_params.get("include_related", "true")).lower() == "true"
        # Retrieve all the columns that are in the db for this organization
        db_columns = Column.retrieve_all(
            org_id=org_id,
            inventory_type=inventory_type,
            only_used=False,
            include_related=include_related,
        )

        self.org = org
        self.cycle = cycle
        self.inventory_type = inventory_type
        self.page = page
        self.per_page = per_page
        self.access_level_instance = access_level_instance
        self.ids_only = ids_only
        self.include_related = include_related
        self.db_columns = db_columns
        self.shown_column_ids = shown_column_ids
        # Level names (skip root at index 0) used as column IDs in the Angular grid
        self.ali_level_names = set(org.access_level_names[1:] if org.access_level_names else [])

    def get_views_list(self):
        """Initial view filter, returns as queryset"""
        if self.inventory_type == "property":
            views_list = PropertyView.objects.select_related("property", "state", "cycle").filter(
                property__organization_id=self.org.id,
                cycle=self.cycle,
                # this is a m-to-1-to-1, so the joins not _that_ bad
                # should it prove to be un-performant, I think we can make it a "through" field
                property__access_level_instance__lft__gte=self.access_level_instance.lft,
                property__access_level_instance__rgt__lte=self.access_level_instance.rgt,
            )
        elif self.inventory_type == "taxlot":
            views_list = TaxLotView.objects.select_related("taxlot", "state", "cycle").filter(
                taxlot__organization_id=self.org.id,
                cycle=self.cycle,
                # this is a m-to-1-to-1, so the joins not _that_ bad
                # should it prove to be un-performant, I think we can make it a "through" field
                taxlot__access_level_instance__lft__gte=self.access_level_instance.lft,
                taxlot__access_level_instance__rgt__lte=self.access_level_instance.rgt,
            )
        else:
            raise InventoryFilterError(
                JsonResponse(
                    {"status": "error", "message": "Invalid inventory type. Must be property or taxlot"}, status=status.HTTP_400_BAD_REQUEST
                )
            )

        return views_list

    def ag_filter_sort_views_list(self, views_qs):
        """Applies AG Grid filters and sorts to the views queryset"""
        # AG Grid fields are the columns' names, formatted as `{column_name}_{id}`, ex: pm_property_id_123
        self.columns_by_name = {c["name"]: c for c in self.db_columns}

        try:
            filters, annotations = self.filters_to_q(
                self.request.data.get("filters"), self.db_columns, self.inventory_type, self.org.access_level_names, self.org
            )
        except FilterError as e:
            raise InventoryFilterError(JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)) from e
        sorts = self.generate_sorts(self.request.data.get("sorts"))
        try:
            return views_qs.annotate(**annotations).filter(filters).order_by(*sorts).distinct()
        except (ValueError, ValidationError) as e:
            # e.g., text filter values on number or date columns
            raise InventoryFilterError(
                JsonResponse(
                    {
                        "status": "error",
                        "recommended_action": "update_column_settings",
                        "message": f"Error filtering - your data might not match the column settings data type: {e!s}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ) from e

    def generate_q_filters(self, filters_dict):
        """generates a Q object for all incoming filters"""
        if not filters_dict:
            return Q()
        if not isinstance(filters_dict, dict):
            raise FilterError("Invalid filters")
        qs = [self.generate_q(k, v) for k, v in filters_dict.items()]
        combined_Q = reduce(and_, qs)
        return combined_Q

    def generate_q(self, name_with_id, filter_dict):
        """generate a Q object from a filter dict"""
        # Even for unknown columns, so that legacy filter groups' `{name}__{lookup}` filters aren't silently ignored
        self.validate_filter(name_with_id, filter_dict)
        # Access level columns are named by level (not `{column_name}_{id}`), with values in the access level path
        if name_with_id in self.ali_level_names:
            column = {"column_name": name_with_id, "access_level": True, "is_extra_data": False, "derived_column": None, "related": False}
        # Ignore unknown columns (e.g., deleted since the filter was saved), as the v3 API does
        elif (column := self.columns_by_name.get(name_with_id)) is None:
            return Q()

        conditions = filter_dict.get("conditions")
        operator = filter_dict.get("operator")
        if conditions and operator:
            # Conditions without a filter type have their filter's
            conditions = [
                {**condition, "filterType": condition.get("filterType") or filter_dict.get("filterType")} for condition in conditions
            ]
            return self.parse_conditions(column, conditions, operator)
        elif filter_dict.get("type"):
            return self.parse_filter(column, filter_dict)
        else:
            raise FilterError(f'Invalid filter for "{name_with_id}"')

    @staticmethod
    def validate_filter(name_with_id, filter_dict):
        """
        Raise a FilterError unless the filter is shaped like an AG Grid filter model (e.g., in a hand-built filter group):
        a condition, or conditions joined by an `operator`, with text types and dates and scalar values
        """
        conditions = (filter_dict.get("conditions") or []) if isinstance(filter_dict, dict) else None
        if not isinstance(conditions, list) or (conditions and not isinstance(filter_dict.get("operator"), str)):
            raise FilterError(f'Invalid filter for "{name_with_id}"')
        for condition in [filter_dict, *conditions]:
            if not (
                isinstance(condition, dict)
                and all(isinstance(condition.get(key), str | None) for key in ("filterType", "type", "dateFrom", "dateTo"))
                and all(isinstance(condition.get(key), str | int | float | None) for key in ("filter", "filterTo"))
            ):
                raise FilterError(f'Invalid filter for "{name_with_id}"')

    def parse_filter(self, column, filter_dict):
        """Convert a filter (a `filterType` of text, number, or date, its `type`, and values) on a column to a Q object"""
        filter_type = filter_dict.get("filterType") or "text"
        condition = filter_dict.get("type")
        # AG Grid keeps a filter's values when it changes its type (e.g., for a filter saved when the grid inferred a
        # column's type from its values), so a date filter's values make it a date filter
        if filter_dict.get("filter") is None and filter_dict.get("dateFrom") is not None:
            filter_type = "date"
        # AG Grid's filter for boolean values: "Choose one" (no filter), True, and False
        if filter_type == "text" and condition in {"empty", "true", "false"}:
            if condition == "empty":
                return Q()
            filter_dict, condition = {**filter_dict, "filter": condition}, "equals"
        if condition not in FILTER_CONDITIONS.get(filter_type, ()):
            raise FilterError(f'Invalid {filter_type} filter "{condition}"')
        if not column["related"]:
            return self.condition_q(column, "state__", filter_type, condition, filter_dict)

        # Related columns match if any related record does, and negated conditions if none does
        other_type = "property" if self.inventory_type == "taxlot" else "taxlot"
        related = TaxLotProperty.objects.filter(**{f"{self.inventory_type}_view": OuterRef("pk")})
        # Related time stamps are their Property's or TaxLot's (see `TaxLotProperty.get_related`), other values their state's
        timestamp = column["column_name"] in {"created", "updated"} and self.get_field_type(column)
        prefix = f"{other_type}_view__{other_type if timestamp else 'state'}__"

        def any_related(condition):
            q = self.condition_q(column, prefix, filter_type, condition, filter_dict)
            return Q(Exists(related.filter(q)))

        if condition == "blank":
            return ~any_related("notBlank")
        if filter_type == "text" and condition in NEGATED_TEXT_CONDITIONS:
            return ~any_related(NEGATED_TEXT_CONDITIONS[condition])
        if condition == "notEqual":
            return any_related("notBlank") & ~any_related("equals")
        return any_related(condition)

    def condition_q(self, column, prefix, filter_type, condition, filter_dict):
        """A filter condition on a column's value, as a Q object, through `prefix` to its record (ex: 'state__')"""
        field_type = self.get_field_type(column)
        value = self.get_value(column, prefix)
        text = value if field_type in STRING_FIELD_TYPES else Cast(value, TextField())
        blank = Q(IsNull(value, True)) | Q(Exact(text, ""))
        if condition == "blank":
            return blank
        if condition == "notBlank":
            return ~blank

        # Values are in `filter` and `filterTo`, or a date filter's `dateFrom` and `dateTo`. AG Grid keeps them when it
        # changes a filter's type, e.g., for a filter saved when the grid inferred a column's type from its values
        start, end = (
            next((filter_dict[key] for key in keys if filter_dict.get(key) is not None), None) for keys in VALUE_KEYS[filter_type]
        )
        if filter_type == "text":
            if start is None:
                raise FilterError(f'Invalid filter value for "{condition}"')
            positive = NEGATED_TEXT_CONDITIONS.get(condition, condition)
            q = Q(TEXT_LOOKUPS[positive](text, str(start)))
            # Negated text conditions include blanks
            return Q(IsNull(text, True)) | ~q if condition in NEGATED_TEXT_CONDITIONS else q

        if filter_type == "number":
            value = self.get_number(column, value, text, field_type)
            start, end = self.parse_number(start), self.parse_number(end)
        else:
            value = self.get_day(column, value, text, field_type)
            start, end = self.parse_day(start, field_type), self.parse_day(end, field_type)
        if start is None:
            raise FilterError(f'Invalid filter value for "{condition}"')
        if condition == "notEqual":
            # Not blanks, but values that aren't numbers or dates
            return ~blank & (Q(IsNull(value, True)) | ~Q(Exact(value, start)))
        if condition == "inRange":
            # Excluding both ends, as the grid does
            if end is None:
                raise FilterError('Invalid filter value for "inRange"')
            return Q(GreaterThan(value, start)) & Q(LessThan(value, end))
        return Q(COMPARISONS[condition](value, start))

    def get_value(self, column, prefix):
        """A column's stored value through `prefix` to its record: a model field, or JSON text (null if missing or null)"""
        if column.get("access_level"):
            return json_text(F(f"{self.inventory_type}__access_level_instance__path"), column["column_name"])
        if column["is_extra_data"]:
            return json_text(F(f"{prefix}extra_data"), column["column_name"])
        if column["derived_column"]:
            return json_text(F(f"{prefix}derived_data"), column["column_name"])
        return F(f"{prefix}{column['column_name']}")

    def get_number(self, column, value, text, field_type):
        """A column's value as a number, as the grid shows it (null for text that isn't a number)"""
        if field_type in NUMBER_FIELD_TYPES:
            number = Cast(value, FloatField())
        else:
            digits = Replace(text, Value(","), Value(""), output_field=TextField())
            number = Case(When(Regex(digits, NUMBER_PATTERN), then=Cast(digits, FloatField())))

        # Quantities show in the organization's display units, rounded (see `apply_display_unit_preferences`)
        if self.org and (base_units := self.get_base_units(column, field_type)):
            quantity = 1 * ureg(base_units)
            factor = quantity.to(display_units(self.org, quantity)).magnitude
            converted = round_half_even(number * Value(factor), self.org.display_decimal_places)
            # but extra data with thousands separators shows as stored (see `TaxLotProperty.extra_data_to_dict_with_mapping`)
            number = converted if field_type else Case(When(Regex(text, NUMBER_PATTERN), then=converted), default=number)
        return number

    @staticmethod
    def get_day(column, value, text, field_type):
        """A column's value as a day: a date, or "YYYY-MM-DD" text (null for text that isn't one)"""
        if field_type == "DateField":
            return value
        if field_type == "DateTimeField":
            # The day shown, as serialized by `TaxLotProperty.model_to_dict_with_mapping`
            naive = column["column_name"] in TaxLotProperty.NAIVE_DATE_TIME_FIELDS
            return TruncDate(value, tzinfo=get_current_timezone() if naive else UTC)
        if field_type in STRING_FIELD_TYPES:
            return Case(When(Regex(text, DATE_PATTERN), then=Left(text, 10)))
        raise FilterError(f'Invalid date filter for "{column["column_name"]}"')

    @staticmethod
    def parse_number(value):
        """A filter's number, which may have thousands separators, or None if it has none"""
        if value is None:
            return None
        try:
            return float(str(value).replace(",", ""))
        except ValueError as e:
            raise FilterError(f'Invalid number "{value}"') from e

    @staticmethod
    def parse_day(value, field_type):
        """A date filter's day (from "YYYY-MM-DD hh:mm:ss", ignoring the time), or None if it has none"""
        if value is None:
            return None
        try:
            date_time = datetime.fromisoformat(value)
        except (TypeError, ValueError) as e:
            raise FilterError(f'Invalid date "{value}"') from e
        if date_time.tzinfo:
            raise FilterError(f'Invalid date "{value}", which has a time zone')
        return date_time.date() if field_type in {"DateField", "DateTimeField"} else date_time.date().isoformat()

    def parse_conditions(self, column, conditions, operator):
        """handle multiple conditions and convert to a single Q object"""
        operator_map = {"AND": and_, "OR": or_}
        if operator not in operator_map:
            raise FilterError(f'Invalid filter operator "{operator}"')
        return reduce(operator_map[operator], [self.parse_filter(column, condition) for condition in conditions])

    @staticmethod
    def get_field_type(column):
        """A column's model field type (e.g., 'CharField'), or None for JSON values (extra data, derived, and access level)"""
        if column.get("access_level") or column["is_extra_data"] or column["derived_column"]:
            return None
        return apps.get_model("seed", column["table_name"])._meta.get_field(column["column_name"]).get_internal_type()

    @staticmethod
    def get_base_units(column, field_type):
        """The units a quantity column's values are stored in, or None if it isn't one"""
        if field_type is None:
            # Related extra and derived data show as stored (see `TaxLotProperty.get_related`)
            return None if column.get("access_level") or column["related"] else DEFAULT_UNITS.get(column.get("data_type"))
        return getattr(apps.get_model("seed", column["table_name"])._meta.get_field(column["column_name"]), "base_units", None)

    def get_filter_type(self, column):
        """
        A column's type for the grid's filter and display: 'text', 'number', 'date', or 'boolean' (a text filter of true or
        false), or None if the server can't filter it
        """
        if column is None:
            return None
        field_type = self.get_field_type(column)
        if field_type is None:
            # Derived values are always numbers
            db_type = "float" if column["derived_column"] else Column.DB_TYPES.get(column["data_type"])
            filter_types = {"float": "number", "integer": "number", "date": "date", "datetime": "date", "boolean": "boolean"}
            filter_type = filter_types.get(db_type, "text")
        elif field_type in NUMBER_FIELD_TYPES:
            filter_type = "number"
        elif field_type in {"DateField", "DateTimeField"}:
            filter_type = "date"
        elif field_type in {"CharField", "TextField", "BooleanField"}:
            filter_type = "boolean" if field_type == "BooleanField" else "text"
        else:
            # Not geometry, whose stored text isn't what the grid shows
            return None
        # Related values show joined as text (see `parse_related_results`)
        return "text" if filter_type == "boolean" and column["related"] else filter_type

    def get_lookup(self, column):
        """
        The ORM lookup for a column's values, ex: 'state__field', 'state__extra_data__field', 'state__derived_data__field'
        Related columns (property -> taxlot) are prefixed with 'taxlotproperty__taxlot_view__'
        """
        other_type = "property" if self.inventory_type == "taxlot" else "taxlot"
        lookup = f"taxlotproperty__{other_type}_view__state__" if column["related"] else "state__"
        if column["is_extra_data"]:
            lookup += "extra_data__"
        elif column["derived_column"]:
            lookup += "derived_data__"
        return lookup + column["column_name"]

    def generate_sorts(self, ag_sorts):
        """
        Generates an array of sort strings for the django orm
        sorts = ['state__field', '-state__field', 'state__extra_data__field', '-state__derived_data__field']
        """
        sorts = []
        for sort in ag_sorts or []:
            direction = "-" if sort.startswith("-") else ""
            column = self.columns_by_name.get(sort.removeprefix("-"))
            # Ignore unknown columns and related columns, which aren't sortable (see `get_column_defs`)
            if column is not None and not column["related"]:
                sorts.append(f"{direction}{self.get_lookup(column)}")

        return sorts

    def include_exclude_views_list(self, views_qs):
        """applies include and exclude ids to the views list"""
        # return property views limited to the 'include_view_ids' list if not empty
        if self.request.data.get("include_view_ids"):
            views_qs = views_qs.filter(id__in=self.request.data["include_view_ids"])

        # exclude property views limited to the 'exclude_view_ids' list if not empty
        if self.request.data.get("exclude_view_ids"):
            views_qs = views_qs.exclude(id__in=self.request.data["exclude_view_ids"])

        # return property views limited to the 'include_property_ids' list if not empty
        if include_property_ids := self.request.data.get("include_property_ids"):
            views_qs = views_qs.filter(property__id__in=include_property_ids)

        return views_qs

    def get_id_list(self, views_list):
        id_list = list(views_list.values_list("id", flat=True))
        return JsonResponse({"results": id_list})

    def get_paginator(self, views_list):
        """paginates the views list, returns views as a paginator object"""
        self.paginator = Paginator(views_list, self.per_page)

        try:
            views = self.paginator.page(self.page)
            self.page = int(self.page)
        except PageNotAnInteger:
            views = self.paginator.page(1)
            self.page = 1
        except EmptyPage:
            views = self.paginator.page(self.paginator.num_pages)
            self.page = self.paginator.num_pages
        except DataError as e:
            raise InventoryFilterError(
                JsonResponse(
                    {
                        "status": "error",
                        "recommended_action": "update_column_settings",
                        "message": f"Error filtering - your data might not match the column settings data type: {e!s}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ) from e
        except IndexError as e:
            raise InventoryFilterError(
                JsonResponse(
                    {"status": "error", "message": f"Error filtering - Clear filters and try again: {e!s}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ) from e

        return views

    def get_profile(self):
        """The organization's list profile for the inventory type, or None if `profile_id` isn't one (e.g., -1)"""
        if not self.profile_id:
            return None
        profile_inventory_type = VIEW_LIST_PROPERTY if self.inventory_type == "property" else VIEW_LIST_TAXLOT
        return ColumnListProfile.objects.filter(
            organization_id=self.org.id, id=self.profile_id, profile_location=VIEW_LIST, inventory_type=profile_inventory_type
        ).first()

    def get_show_columns(self):
        # This uses an old method of returning the show_columns. There is a new method that
        # is preferred in v2.1 API with the ProfileIdMixin.
        show_columns: list[int] | None = None
        if self.shown_column_ids and self.profile_id:
            raise InventoryFilterError(
                JsonResponse(
                    {
                        "status": "error",
                        "recommended_action": "update_column_settings",
                        "message": 'Error filtering - "shown_column_ids" and "profile_id" are mutually exclusive.',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            )

        elif self.shown_column_ids is not None:
            self.shown_column_ids = self.shown_column_ids.split(",")
            show_columns = list(
                Column.objects.filter(organization_id=self.org.id, id__in=self.shown_column_ids).values_list("id", flat=True)
            )
        elif self.profile_id is None:
            show_columns = None
        elif self.profile_id == -1:
            show_columns = list(Column.objects.filter(organization_id=self.org.id).values_list("id", flat=True))
        elif profile := self.get_profile():
            show_columns = list(
                ColumnListProfileColumn.objects.filter(column_list_profile_id=profile.id).values_list("column_id", flat=True)
            )

        return show_columns

    def serialize_views(self, views, show_columns):
        """serialize the views"""
        try:
            related_results = TaxLotProperty.serialize(views, show_columns, self.db_columns, self.include_related)
        except DataError as e:
            raise InventoryFilterError(
                JsonResponse(
                    {
                        "status": "error",
                        "recommended_action": "update_column_settings",
                        "message": f"Error filtering - your data might not match the column settings data type: {e!s}",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            ) from e

        return related_results

    def parse_related_results(self, results):
        """add related data as a semicolon separated list"""
        if not self.include_related:
            return results

        for result in results:
            parsed_fields = {}
            for related in result.get("related", []):
                # create a set of unique values for each valid field
                for field, value in related.items():
                    # Dates and date times (e.g., year_ending and created) as the response encodes this record's own
                    val = DjangoJSONEncoder().default(value) if isinstance(value, date) else value
                    if self.valid_related_field(field, val):
                        parsed_fields.setdefault(field, set()).add(val)

            # convert sets to semicolon-separated strings
            for field, values in parsed_fields.items():
                result[field] = "; ".join(str(v) for v in sorted(values))

        return results

    def valid_related_field(self, field, value):
        """determine if column has format {column_name}_{id}"""
        excluded_fields = [
            "bounding_box",
            "centroid",
            "id",
            "long_lat",
            "merged_indicator",
            "notes_count",
            "taxlot_state_id",
            "taxlot_view_id",
            "property_state_id",
            "property_view_id",
        ]
        if field in excluded_fields:
            return False
        if not isinstance(value, (str, int, float)):  # IS THIS NECESSARY? are booleans no ignored?
            return False
        # Regex check if field ends with _{int}
        return bool(re.search(r"_\d+$", field))

    def get_column_defs(self):
        """Build out the column defs for AG grid, other inventory fields are not sortable"""
        table_map = {"property": ["PropertyState", "TaxLotState", "(Tax Lot)"], "taxlot": ["TaxLotState", "PropertyState", "(Property)"]}
        table, other_table, other_suffix = table_map.get(self.inventory_type, ["PropertyState", "TaxLotState"])

        # Use the same profile as `get_show_columns`, or all columns when there is none (e.g., -1)
        if profile := self.get_profile():
            profile = ColumnListProfileSerializer(profile).data
            columns = [c for c in profile["columns"] if c["table_name"] == table]
            other_columns = [c for c in profile["columns"] if c["table_name"] == other_table]
        else:
            columns = Column.objects.filter(organization_id=self.org.id, table_name=table)
            columns = ColumnSerializer(columns, many=True).data
            other_columns = Column.objects.filter(organization_id=self.org.id, table_name=other_table)
            other_columns = ColumnSerializer(other_columns, many=True).data

        def filter_props(column):
            """The grid filters on the server, which tells it each column's filter type, or not to filter one it can't"""
            filter_type = self.get_filter_type(self.columns_by_name.get(column["name"]))
            return {"context": {"filterType": filter_type}} if filter_type else {"filter": False}

        column_defs = [{"field": c["name"], "headerName": c["display_name"], **filter_props(c)} for c in columns]

        if self.include_related:
            other_column_defs = [
                {"field": c["name"], "headerName": f"{c['display_name']} {other_suffix}", "sortable": False, **filter_props(c)}
                for c in other_columns
            ]

            column_defs.extend(other_column_defs)

        return column_defs

    def build_response(self, results, column_defs):
        response = {
            "pagination": {
                "page": self.page,
                "start": self.paginator.page(self.page).start_index(),
                "end": self.paginator.page(self.page).end_index(),
                "num_pages": self.paginator.num_pages,
                "has_next": self.paginator.page(self.page).has_next(),
                "has_previous": self.paginator.page(self.page).has_previous(),
                "total": self.paginator.count,
            },
            "cycle_id": self.cycle.id,
            "results": results,
            "column_defs": column_defs,
        }

        return response
