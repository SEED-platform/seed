"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re
from functools import reduce
from operator import and_, or_

from django.apps import apps
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.db.utils import DataError
from django.http import JsonResponse
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
from seed.serializers.pint import apply_display_unit_preferences


class InventoryFilterError(Exception):
    """Custom exception for inventory filter errors"""

    def __init__(self, response: JsonResponse):
        self.response = response


class InventoryFilter:
    Q_MAP = {
        "contains": lambda name, filter, _: Q(**{f"{name}__icontains": filter}),  # noqa: A006
        "notContains": lambda name, filter, _: ~Q(**{f"{name}__icontains": filter}),  # noqa: A006
        "equals": lambda name, filter, _: Q(**{f"{name}": filter}),  # noqa: A006
        "notEqual": lambda name, filter, _: ~Q(**{f"{name}": filter}),  # noqa: A006
        "startsWith": lambda name, filter, _: Q(**{f"{name}__istartswith": filter}),  # noqa: A006
        "endsWith": lambda name, filter, _: Q(**{f"{name}__iendswith": filter}),  # noqa: A006
        "blank": lambda name, *_: Q(**{f"{name}__isnull": True}) | Q(**{f"{name}": ""}),
        "notBlank": lambda name, *_: Q(**{f"{name}__isnull": False}) & ~Q(**{f"{name}": ""}),
        "isNull": lambda name, *_: Q(**{f"{name}__isnull": True}),
        "notNull": lambda name, *_: Q(**{f"{name}__isnull": False}),
        "greaterThan": lambda name, filter, _: Q(**{f"{name}__gt": filter}),  # noqa: A006
        "greaterThanOrEqual": lambda name, filter, _: Q(**{f"{name}__gte": filter}),  # noqa: A006
        "lessThan": lambda name, filter, _: Q(**{f"{name}__lt": filter}),  # noqa: A006
        "lessThanOrEqual": lambda name, filter, _: Q(**{f"{name}__lte": filter}),  # noqa: A006
        "inRange": lambda name, filter, filter_to: Q(**{f"{name}__gt": filter, f"{name}__lt": filter_to}),  # noqa: A006
    }

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

        filters = self.generate_q_filters(self.request.data.get("filters"))
        sorts = self.generate_sorts(self.request.data.get("sorts"))
        try:
            return views_qs.filter(filters).order_by(*sorts).distinct()
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
        qs = [self.generate_q(k, v) for k, v in filters_dict.items()]
        combined_Q = reduce(and_, qs)
        return combined_Q

    def generate_q(self, name_with_id, filter_dict):
        """generate a Q object from a filter dict"""
        # Access level instance columns use the level name directly (not colname_id format)
        if name_with_id in self.ali_level_names:
            return self.generate_ali_q(name_with_id, filter_dict)

        # Ignore unknown columns (e.g., deleted since the filter was saved), as the v3 API does
        if (column := self.columns_by_name.get(name_with_id)) is None:
            return Q()

        conditions = filter_dict.get("conditions")
        operator = filter_dict.get("operator")
        if conditions and operator:
            return self.parse_conditions(column, conditions, operator)
        elif filter_dict.get("type"):
            return self.parse_filter(column, filter_dict)
        else:
            raise InventoryFilterError(JsonResponse({"status": "error", "message": "Invalid filter"}, status=status.HTTP_400_BAD_REQUEST))

    def generate_ali_q(self, level_name, filter_dict):
        """Generate a Q for filtering by an access level instance path column."""
        inventory_prefix = "property" if self.inventory_type == "property" else "taxlot"
        path_field = f"{inventory_prefix}__access_level_instance__path"
        prefixed = f"{path_field}__{level_name}"
        filter_value = filter_dict.get("filter")
        filter_type = filter_dict.get("type", "contains")

        type_map = {
            "contains": Q(**{f"{prefixed}__icontains": filter_value}),
            "notContains": ~Q(**{f"{prefixed}__icontains": filter_value}),
            "equals": Q(**{f"{prefixed}__iexact": filter_value}),
            "notEqual": ~Q(**{f"{prefixed}__iexact": filter_value}),
            "startsWith": Q(**{f"{prefixed}__istartswith": filter_value}),
            "endsWith": Q(**{f"{prefixed}__iendswith": filter_value}),
            "blank": ~Q(**{f"{path_field}__has_key": level_name}),
            "notBlank": Q(**{f"{path_field}__has_key": level_name}),
            "isNull": ~Q(**{f"{path_field}__has_key": level_name}),
            "notNull": Q(**{f"{path_field}__has_key": level_name}),
        }

        return type_map.get(filter_type, Q())

    def parse_filter(self, column, filter_dict):
        """convert a single filter (`type`, `filter`, and `filterTo`) on a column to a Q object"""
        lookup = self.get_lookup(column)
        filter_type = filter_dict.get("type")
        is_json = column["is_extra_data"] or column["derived_column"]
        # Only strings and JSON values can be "" (comparing other types with it raises), so other blanks are nulls
        if not (is_json or self.is_string_field(column)):
            filter_type = {"blank": "isNull", "notBlank": "notNull"}.get(filter_type, filter_type)

        q = self.Q_MAP[filter_type](lookup, filter_dict.get("filter"), filter_dict.get("filterTo"))
        # JSON values can be null (e.g., derived values that can't be computed), which `__isnull` treats as present.
        # Not for related columns, where negating a null match would exclude records with any null related value
        if is_json and not column["related"]:
            if filter_type in {"blank", "isNull"}:
                q |= Q(**{lookup: None})
            elif filter_type in {"notBlank", "notNull"}:
                q &= ~Q(**{lookup: None})
        return q

    def parse_conditions(self, column, conditions, operator):
        """handle multiple conditions and convert to a single Q object"""
        operator_map = {"AND": and_, "OR": or_}
        return reduce(operator_map[operator], [self.parse_filter(column, condition) for condition in conditions])

    @staticmethod
    def is_string_field(column):
        """Whether a column is a string model field (not extra data or a derived column)"""
        field = apps.get_model("seed", column["table_name"])._meta.get_field(column["column_name"])
        return field.get_internal_type() in {"CharField", "TextField"}

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
                for field, val in related.items():
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

        column_defs = [
            {
                "field": c["name"],
                "headerName": c["display_name"],
                # **({"pinned": "left"} if c.get("pinned") else {})
            }
            for c in columns
        ]

        if self.include_related:
            other_column_defs = [
                {"field": c["name"], "headerName": f"{c['display_name']} {other_suffix}", "sortable": False} for c in other_columns
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
