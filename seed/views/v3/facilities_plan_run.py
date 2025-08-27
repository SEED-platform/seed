"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

import io
import logging
from pathlib import Path
from typing import Literal, Union

import pandas as pd
from django.contrib.postgres.expressions import ArraySubquery
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, FilteredRelation, OuterRef, Q
from django.db.utils import DataError
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action
from styleframe import StyleFrame

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.lib.tkbl.tkbl import EISA432_CODES
from seed.models import AccessLevelInstance, Column, Element, FacilitiesPlanRun, Organization, TaxLotProperty
from seed.serializers.facilities_plan_run import FacilitiesPlanRunSerializer
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.api import api_endpoint
from seed.utils.search import FilterError, build_view_filters_and_sorts
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

logger = logging.getLogger(__name__)


@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        # has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(body_ali_id="ali"),
    ],
    name="create",
)
class FacilitiesPlanRunViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    serializer_class = FacilitiesPlanRunSerializer
    model = FacilitiesPlanRun
    pagination_class = None

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        fprs = FacilitiesPlanRun.objects.filter(ali__organization=org_id)

        access_level_instance_id = getattr(self.request, "access_level_instance_id", None)
        if access_level_instance_id:
            access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
            fprs = fprs.filter(ali__lft__gte=access_level_instance.lft, ali__rgt__lte=access_level_instance.rgt)

        return fprs

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def properties(self, request, pk):
        """
        Properties
        """
        # Init a bunch of values
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            fpr = FacilitiesPlanRun.objects.get(pk=pk)
        except (Organization.DoesNotExist, FacilitiesPlanRun.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        page = request.query_params.get("page", 1)
        per_page = request.query_params.get("per_page", 100)
        inventory_type: Union[Literal["property", "taxlot"]] = "property"
        access_level_instance = fpr.ali
        columns_from_database = Column.retrieve_all(
            org_id=org_id,
            inventory_type=inventory_type,
            only_used=False,
            include_related=False,
        )
        show_columns = [
            c.id
            for c in [
                Column.objects.filter(table_name="PropertyState", column_name=org.property_display_field, organization=org).first(),
                fpr.facilities_plan.compliance_cycle_year_column,
                fpr.facilities_plan.include_in_total_denominator_column,
                fpr.facilities_plan.exclude_from_plan_column,
                fpr.facilities_plan.require_in_plan_column,
                fpr.facilities_plan.electric_energy_usage_column,
                fpr.facilities_plan.gas_energy_usage_column,
                fpr.facilities_plan.steam_energy_usage_column,
            ]
            if c is not None
        ] + list(fpr.display_columns.values_list("id", flat=True))

        # get views
        views = (
            fpr.cycle.propertyview_set.filter(
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )
            .annotate(run_info=FilteredRelation("facility_plan_runs", condition=(Q(facility_plan_runs__run_id=fpr.id))))
            .order_by("run_info__rank")
        )

        try:
            filters, annotations, order_by = build_view_filters_and_sorts(
                request.query_params, columns_from_database, inventory_type, org.access_level_names
            )
            if order_by == ["id"]:
                order_by = ["run_info__rank"]
            views = views.annotate(**annotations).filter(filters).order_by(*order_by)
        except FilterError as e:
            return JsonResponse({"status": "error", "message": f"Error filtering: {e!s}"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return JsonResponse({"status": "error", "message": f"Error filtering: {e!s}"}, status=status.HTTP_400_BAD_REQUEST)

        if request.query_params.get("only_ids", "false") == "true":
            return JsonResponse({"ids": list(views.values_list("id", flat=True))})

        # get views run info for later
        view_run_infos = views.values(
            "run_info__rank",
            "run_info__total_energy_usage",
            "run_info__percentage_of_total_energy_usage",
            "run_info__running_percentage",
            "run_info__running_square_footage",
        )

        # Paginate results
        paginator = Paginator(views, per_page)
        try:
            views = paginator.page(page)
            page = int(page)
        except PageNotAnInteger:
            views = paginator.page(1)
            page = 1
        except EmptyPage:
            views = paginator.page(paginator.num_pages)
            page = paginator.num_pages
        except DataError as e:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Error filtering - your data might not match the column settings data type: {e!s}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IndexError as e:
            return JsonResponse(
                {"status": "error", "message": f"Error filtering - Clear filters and try again: {e!s}"}, status=status.HTTP_400_BAD_REQUEST
            )

        # collapse pint quantity units to their magnitudes
        properties = TaxLotProperty.serialize(views, show_columns, columns_from_database, False, pk)
        properties = [apply_display_unit_preferences(org, x) for x in properties]

        if paginator.page(page).start_index() > 0:
            for property_json, run_info in zip(
                properties, view_run_infos[paginator.page(page).start_index() - 1 : paginator.page(page).end_index()]
            ):
                property_json["total_energy_usage"] = run_info["run_info__total_energy_usage"]
                property_json["percentage_of_total_energy_usage"] = run_info["run_info__percentage_of_total_energy_usage"]
                property_json["running_percentage"] = run_info["run_info__running_percentage"]
                property_json["running_square_footage"] = run_info["run_info__running_square_footage"]
                # compliance_cycle_year_column = fpr.facilities_plan.compliance_cycle_year_column
                # column_name = compliance_cycle_year_column.display_name if compliance_cycle_year_column.display_name else compliance_cycle_year_column.column_name

        return JsonResponse(
            {
                "pagination": {
                    "page": page,
                    "start": paginator.page(page).start_index(),
                    "end": paginator.page(page).end_index(),
                    "num_pages": paginator.num_pages,
                    "has_next": paginator.page(page).has_next(),
                    "has_previous": paginator.page(page).has_previous(),
                    "total": paginator.count,
                },
                "properties": properties,
            }
        )

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def run(self, request, pk):
        try:
            fpr = FacilitiesPlanRun.objects.get(pk=pk)
        except (Organization.DoesNotExist, FacilitiesPlanRun.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        fpr.run()

        return JsonResponse({"status": "success"})

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["POST"])
    def export(self, request, pk):
        # get are fpr ready
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            fpr = FacilitiesPlanRun.objects.get(pk=pk)
        except (Organization.DoesNotExist, FacilitiesPlanRun.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        # import blank template
        BLANK_CTS_FILE_PATH = Path(__file__).parents[2] / "utils" / "facilities_plan_output.xlsx"
        hot_to_df = pd.read_excel(BLANK_CTS_FILE_PATH, sheet_name="How To Guide")
        properties_df = pd.read_excel(BLANK_CTS_FILE_PATH, sheet_name="1. Facilities Plan")
        components_df = pd.read_excel(BLANK_CTS_FILE_PATH, sheet_name="2. Prioritized Bldg Components")
        data_dictionary_df = pd.read_excel(BLANK_CTS_FILE_PATH, sheet_name="3. ECM Data Dictionary")

        # populate properties_df
        properties_df, components_df = self._populate_properties_and_components(fpr, org)

        # put it in a styleframe
        how_to_sf = StyleFrame.read_excel_as_template(BLANK_CTS_FILE_PATH, df=hot_to_df, sheet_name="How To Guide")
        # properties_sf = StyleFrame.read_excel_as_template(BLANK_CTS_FILE_PATH, df=properties_df, sheet_name="1. Facilities Plan")
        # components_sf = StyleFrame.read_excel_as_template(BLANK_CTS_FILE_PATH, df=components_df, sheet_name="2. Prioritized Bldg Components")
        data_dictionary_sf = StyleFrame.read_excel_as_template(
            BLANK_CTS_FILE_PATH, df=data_dictionary_df, sheet_name="3. ECM Data Dictionary"
        )

        # write it back out
        output = io.BytesIO()
        with StyleFrame.ExcelWriter(output) as writer:
            how_to_sf.to_excel(writer, sheet_name="How To Guide", index=False)
            properties_df.to_excel(writer, sheet_name="1. Facilities Plan", index=False)
            components_df.to_excel(writer, sheet_name="2. Prioritized Bldg Components", index=False)
            data_dictionary_sf.to_excel(writer, sheet_name="3. ECM Data Dictionary", index=False)

        # build response
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="output.xlsx"'
        xlsx_data = output.getvalue()
        response.write(xlsx_data)

        return response

    def _populate_properties_and_components(self, fpr, org):
        # get the columns we care about
        show_columns = [
            # display name
            Column.objects.filter(table_name="PropertyState", column_name=org.property_display_field, organization=org).first(),
            # columns on the fp
            fpr.facilities_plan.compliance_cycle_year_column,
            fpr.facilities_plan.include_in_total_denominator_column,
            fpr.facilities_plan.exclude_from_plan_column,
            fpr.facilities_plan.require_in_plan_column,
            fpr.facilities_plan.electric_energy_usage_column,
            fpr.facilities_plan.gas_energy_usage_column,
            fpr.facilities_plan.steam_energy_usage_column,
            # columns on the fpr
            *list(fpr.display_columns.all()),
        ]

        # get views with run info
        views = (
            fpr.cycle.propertyview_set.filter(
                property__access_level_instance__lft__gte=fpr.ali.lft,
                property__access_level_instance__rgt__lte=fpr.ali.rgt,
            )
            .annotate(run_info=FilteredRelation("facility_plan_runs", condition=(Q(facility_plan_runs__run_id=fpr.id))))
            .order_by("run_info__rank")
        )

        # annotate all the shown columns. the shown columns must be annotated on (instead of
        # simply `.values`ed) as they may have characters (such as spaces) that is disallowed from
        # args of `.values()`
        columns_dict = [
            *[
                {
                    "annotated_name": f"col_{i}",
                    "display_name": column.display_name,
                    "queryable_name": F(_get_column_model_field(column)),
                }
                for i, column in enumerate(show_columns)
            ],
            *[
                #  we need the rank info too
                {
                    "annotated_name": "rank_info_1",
                    "display_name": "Total Energy Usage",
                    "queryable_name": F("run_info__total_energy_usage"),
                },
                {
                    "annotated_name": "rank_info_2",
                    "display_name": "Percentage of Total Energy Usage",
                    "queryable_name": F("run_info__percentage_of_total_energy_usage"),
                },
                {
                    "annotated_name": "rank_info_3",
                    "display_name": "Running Percentage",
                    "queryable_name": F("run_info__running_percentage"),
                },
                {
                    "annotated_name": "rank_info_4",
                    "display_name": "Running Square Footage",
                    "queryable_name": F("run_info__running_square_footage"),
                },
            ],
        ]
        annotations = {cd["annotated_name"]: cd["queryable_name"] for cd in columns_dict}
        views = views.annotate(**annotations)

        # put those in a df
        properties_records = list(views.values(*[cd["annotated_name"] for cd in columns_dict]))
        properties_df = pd.DataFrame.from_records(properties_records)
        properties_df = properties_df.rename(columns={cd["annotated_name"]: cd["display_name"] for cd in columns_dict})

        # get the relevant elements, that is, the top 3 RSL for each property with an EISA code
        top_3_element_query = Element.objects.filter(property=OuterRef("pk"), code__code__in=EISA432_CODES)[:3]
        lists_of_element_ids = views.annotate(elements=ArraySubquery(top_3_element_query.values("id"))).values_list("elements", flat=True)
        element_ids = [element_id for element_ids in lists_of_element_ids for element_id in element_ids]
        elements = Element.objects.filter(id__in=element_ids)

        # annotate all the shown columns. the shown columns must be annotated on (instead of
        # simply `.values`ed) as they may have characters (such as spaces) that is disallowed from
        # args of `.values()`
        columns_dict = [
            {
                "annotated_name": "cat_code",
                "display_name": "Uniformat Category",
                "queryable_name": F("code__code"),
            },
            {
                "annotated_name": "rsl",
                "display_name": "RSL",
                "queryable_name": F("remaining_service_life"),
            },
            {
                "annotated_name": "component_subtype",
                "display_name": "Component_SubType",
                "queryable_name": F("extra_data__Component_SubType"),
            },
            {
                "annotated_name": "sec_id",
                "display_name": "SEC_ID",
                "queryable_name": F("extra_data__SEC_ID"),
            },
            {
                "annotated_name": "section_name",
                "display_name": "Section Name",
                "queryable_name": F("extra_data__Section Name"),
            },
            {
                "annotated_name": "ci",
                "display_name": "CI",
                "queryable_name": F("extra_data__CI"),
            },
            {
                "annotated_name": "replacement_cost_col",
                "display_name": "Replacement Cost",
                "queryable_name": F("replacement_cost"),
            },
            {
                "annotated_name": "capacity_cooling",
                "display_name": "Capacity_cooling",
                "queryable_name": F("extra_data__CAPACITY_COOLING"),
            },
            {
                "annotated_name": "capacity_cooling_units",
                "display_name": "Capacity_cooling_units",
                "queryable_name": F("extra_data__CAPACITY_COOLING_UNITS"),
            },
            {
                "annotated_name": "capacity_heating",
                "display_name": "Capacity_heating",
                "queryable_name": F("extra_data__CAPACITY_HEATING"),
            },
            {
                "annotated_name": "capacity_heating_units",
                "display_name": "Capacity_heating_units",
                "queryable_name": F("extra_data__CAPACITY_HEATING_UNITS"),
            },
            {
                "annotated_name": "flowrate",
                "display_name": "Flowrate",
                "queryable_name": F("extra_data__FLOWRATE"),
            },
            {
                "annotated_name": "flowrate_units",
                "display_name": "Flowrate_units",
                "queryable_name": F("extra_data__FLOWRATE_UNITS"),
            },
            {
                "annotated_name": "fuel_type",
                "display_name": "Fuel_type",
                "queryable_name": F("extra_data__FUEL_TYPE"),
            },
            {
                "annotated_name": "power",
                "display_name": "Power",
                "queryable_name": F("extra_data__POWER"),
            },
            {
                "annotated_name": "power_units",
                "display_name": "Power_units",
                "queryable_name": F("extra_data__POWER_UNITS"),
            },
        ]
        annotations = {cd["annotated_name"]: cd["queryable_name"] for cd in columns_dict}
        elements = elements.annotate(**annotations)
        elements_records = list(elements.values("property_id", *[cd["annotated_name"] for cd in columns_dict]))

        # now we gotta append those property columns
        # get the columns we care about
        show_columns = [
            # display name
            Column.objects.filter(table_name="PropertyState", column_name=org.property_display_field, organization=org).first(),
            # columns on the fpr
            *list(fpr.display_columns.all()),
            # building upgrade recommendation
            Column.objects.filter(table_name="PropertyState", column_name="building_upgrade_recommendation", organization=org).first(),
            # columns on the fp
            fpr.facilities_plan.compliance_cycle_year_column,
        ]

        # annotate all the shown columns. the shown columns must be annotated on (instead of
        # simply `.values`ed) as they may have characters (such as spaces) that is disallowed from
        # args of `.values()`
        columns_dict = [
            {
                "annotated_name": f"col_{i}",
                "display_name": column.display_name,
                "queryable_name": F(_get_column_model_field(column)),
            }
            for i, column in enumerate(show_columns)
        ]
        annotations = {cd["annotated_name"]: cd["queryable_name"] for cd in columns_dict}
        views = views.annotate(**annotations)

        # add property columns to element records
        view_dict_by_id = {v["property_id"]: v for v in views.values("property_id", *[cd["annotated_name"] for cd in columns_dict])}
        for er in elements_records:
            er.update(view_dict_by_id[er["property_id"]])

        # put those in a df
        elements_df = pd.DataFrame.from_records(elements_records)
        elements_df = elements_df.rename(columns={cd["annotated_name"]: cd["display_name"] for cd in columns_dict})

        return properties_df, elements_df


def _get_column_model_field(column):
    if column.is_extra_data:
        return "state__extra_data__" + column.column_name
    elif column.derived_column:
        return "state__derived_data__" + column.column_name
    else:
        return "state__" + column.column_name
