"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re
from functools import reduce
from operator import and_, or_
from typing import Optional

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
        "contains": lambda name, filter, _: Q(**{f"{name}__icontains": filter}),
        "notContains": lambda name, filter, _: ~Q(**{f"{name}__icontains": filter}),
        "equals": lambda name, filter, _: Q(**{f"{name}": filter}),
        "notEqual": lambda name, filter, _: ~Q(**{f"{name}": filter}),
        "startsWith": lambda name, filter, _: Q(**{f"{name}__istartswith": filter}),
        "endsWith": lambda name, filter, _: Q(**{f"{name}__iendswith": filter}),
        "blank": lambda name, *_: Q(**{f"{name}__isnull": True}) | Q(**{f"{name}": ""}),
        "notBlank": lambda name, *_: Q(**{f"{name}__isnull": False}) & ~Q(**{f"{name}": ""}),
        "greaterThan": lambda name, filter, _: Q(**{f"{name}__gt": filter}),
        "greaterThanOrEqual": lambda name, filter, _: Q(**{f"{name}__gte": filter}),
        "lessThan": lambda name, filter, _: Q(**{f"{name}__lt": filter}),
        "lessThanOrEqual": lambda name, filter, _: Q(**{f"{name}__lte": filter}),
        "inRange": lambda name, filter, filter_to: Q(**{f"{name}__gt": filter, f"{name}__lt": filter_to}),
    }

    def __init__(self, request, profile_id=None):
        self.request = request
        self.profile_id = profile_id
        # class vars to be set through get_filtered_results
        self.access_level_instance = None
        self.cycle = None
        self.db_columns = None
        self.extra_data_column_names = None
        self.ids_only = None
        self.include_related = None
        self.inventory_type = None
        self.page = None
        self.paginator = None
        self.per_page = None
        self.org = None
        self.other_column_names_with_id = None
        self.shown_column_ids = None

    def get_filtered_results(self):
        """Main method to get the filtered results"""
        try:
            self.validate_request()
            views_qs = self.get_views_list()
            views_qs = self.ag_filter_sort_views_list(views_qs)
            views_list = self.include_exclude_views_list(views_qs)
            if self.ids_only:
                return self.get_id_list(views_list)
            views_paginated = self.get_paginator(views_list)
            show_columns = self.get_show_columns()
            related_results = self.serialize_views(views_paginated, show_columns)

        except InventoryFilterError as e:
            return e.response

        unit_collapsed_results = [apply_display_unit_preferences(self.org, x) for x in related_results]
        results = self.parse_related_results(unit_collapsed_results)
        column_defs = self.get_column_defs()
        response = self.build_response(results, column_defs)

        return response

    def validate_request(self):
        """validates request, assigns class variables"""
        page = self.request.query_params.get("page", 1)
        per_page = self.request.query_params.get("per_page", 100)
        org_id = self.request.query_params.get("organization_id")
        cycle_id = self.request.query_params.get("cycle")
        inventory_type = self.request.query_params.get("inventory_type")
        ids_only = self.request.query_params.get("ids_only", "false").lower() == "true"
        self.profile_id = self.request.query_params.get("profile_id", self.profile_id)
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
            cycle = Cycle.objects.get(organization_id=org_id, pk=cycle_id)
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

        if ids_only and (per_page or page):
            raise InventoryFilterError(
                JsonResponse(
                    {"success": False, "message": 'Cannot pass query parameter "ids_only" with "per_page" or "page"'},
                    status=status.HTTP_400_BAD_REQUEST,
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
        ag_filters = self.request.data.get("filters")
        ag_sorts = self.request.data.get("sorts")

        other_table = "PropertyState" if self.inventory_type == "taxlot" else "TaxLotState"
        # generate list of other tables column names with ids (as passed by ag grid), ex: pm_property_id_123
        self.other_column_names_with_id = [f"{c['column_name']}_{c['id']}" for c in self.db_columns if c["table_name"] == other_table]
        self.extra_data_column_names = [c["column_name"] for c in self.db_columns if c["is_extra_data"]]

        filters = self.generate_q_filters(ag_filters)
        sorts = self.generate_sorts(ag_sorts)

        views_qs = views_qs.filter(filters).order_by(*sorts).distinct()

        return views_qs

    def generate_q_filters(self, filters_dict):
        """generates a Q object for all incoming filters"""
        if not filters_dict:
            return Q()
        qs = [self.generate_q(k, v) for k, v in filters_dict.items()]
        combined_Q = reduce(and_, qs)
        return combined_Q

    def generate_q(self, name_with_id, filter_dict):
        """generate a Q object from a filter dict"""
        conditions = filter_dict.get("conditions")
        operator = filter_dict.get("operator")
        filter = filter_dict.get("filter")
        filter_to = filter_dict.get("filterTo")
        type = filter_dict.get("type")
        # handles cases when filtering on other table
        prefixed_name = self.parse_name(name_with_id)

        if conditions and operator:
            q = self.parse_conditions(prefixed_name, conditions, operator)
        elif type:
            q = self.parse_filter(prefixed_name, type, filter, filter_to)
        else:
            raise InventoryFilterError(JsonResponse({"status": "error", "message": "Invalid filter"}, status=status.HTTP_400_BAD_REQUEST))
        return q

    def parse_filter(self, prefixed_name, filter_type, filter_from, filter_to=None):
        """convert a single filter to a Q object"""
        return self.Q_MAP[filter_type](prefixed_name, filter_from, filter_to)

    def parse_conditions(self, prefixed_name, conditions, operator):
        """handle multiple conditions and convert to a single Q object"""
        operator_map = {"AND": and_, "OR": or_}
        qs = []

        for condition in conditions:
            type = condition.get("type")
            filter = condition.get("filter")
            filter_to = condition.get("filterTo")
            q = self.Q_MAP[type](prefixed_name, filter, filter_to)
            qs.append(q)

        combine_Q = reduce(operator_map[operator], qs)
        return combine_Q

    def strip_id(self, name_with_id):
        """strips the _id from the end of the column name"""
        parts = name_with_id.rsplit("_", 1)
        if len(parts) != 2:
            raise InventoryFilterError(
                JsonResponse({"status": "error", "message": f"Invalid column name: {name_with_id}"}, status=status.HTTP_400_BAD_REQUEST)
            )
        return parts[0]

    def prefix_name(self, name, related_prefix=""):
        """
        adds 'extra_data__' to name if its an extra data field
        if its a related filter (property -> taxlot) add the related prefix ('taxlotproperty__taxlot_view__')
        else it ignores the related_prefix
        """
        if name in self.extra_data_column_names:
            return f"{related_prefix}state__extra_data__{name}"
        return f"{related_prefix}state__{name}"

    def parse_name(self, name_with_id):
        """If filtering on related table (property -> taxlot) add the related prefix"""
        other_type = "property" if self.inventory_type == "taxlot" else "taxlot"

        name = self.strip_id(name_with_id)
        # conditionally add related prefix to the args
        if name_with_id in self.other_column_names_with_id:
            related_prefix = f"taxlotproperty__{other_type}_view__"
            return self.prefix_name(name, related_prefix)
        else:
            return self.prefix_name(name)

    def generate_sorts(self, ag_sorts):
        """
        Generates an array of sort strings for the django orm
        sorts = ['state__field', '-state__field', 'state__extra_data__field', '-state__extra_data__field']
        """
        sorts = []
        if not ag_sorts:
            return sorts

        for sort in ag_sorts:
            direction = "-" if sort[0] == "-" else ""

            column_name = sort[1:] if direction else sort
            column_name = self.strip_id(column_name)

            prefix = self.prefix_name(column_name)

            sorts.append(f"{direction}{prefix}{column_name}")

        return sorts

    def include_exclude_views_list(self, views_list):
        """applies include and exclude ids to the views list"""
        # return property views limited to the 'include_view_ids' list if not empty
        if self.request.data.get("include_view_ids"):
            views_list = views_list.filter(id__in=self.request.data["include_view_ids"])

        # exclude property views limited to the 'exclude_view_ids' list if not empty
        if self.request.data.get("exclude_view_ids"):
            views_list = views_list.exclude(id__in=self.request.data["exclude_view_ids"])

        # return property views limited to the 'include_property_ids' list if not empty
        if include_property_ids := self.request.data.get("include_property_ids"):
            views_list = views_list.filter(property__id__in=include_property_ids)

        return list(views_list)

    def get_id_list(self, views_list):
        id_list = list(views_list.values_list("id", flat=True))
        return JsonResponse({"results": id_list})

    def get_paginator(self, views_list):
        """pagineates the views list, returns views as a paginator object"""
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
            )
        except IndexError as e:
            raise InventoryFilterError(
                JsonResponse(
                    {"status": "error", "message": f"Error filtering - Clear filters and try again: {e!s}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            )

        return views

    def get_show_columns(self):
        # This uses an old method of returning the show_columns. There is a new method that
        # is preferred in v2.1 API with the ProfileIdMixin.
        if self.inventory_type == "property":
            profile_inventory_type = VIEW_LIST_PROPERTY
        elif self.inventory_type == "taxlot":
            profile_inventory_type = VIEW_LIST_TAXLOT

        show_columns: Optional[list[int]] = None
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
        else:
            try:
                profile = ColumnListProfile.objects.get(
                    organization_id=self.org.id, id=self.profile_id, profile_location=VIEW_LIST, inventory_type=profile_inventory_type
                )
                show_columns = list(
                    ColumnListProfileColumn.objects.filter(column_list_profile_id=profile.id).values_list("column_id", flat=True)
                )
            except ColumnListProfile.DoesNotExist:
                show_columns = None

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
            )

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

        if self.profile_id:
            profile = ColumnListProfile.objects.get(id=self.profile_id)
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
