"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

import logging

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import FilteredRelation, Q
from django.db.utils import DataError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import (
    AccessLevelInstance,
    Column,
    FacilitiesPlanRun,
    Organization,
    TaxLotProperty,
)
from seed.serializers.facilities_plan_run import FacilitiesPlanRunSerializer
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.api import api_endpoint_class
from seed.utils.search import FilterError, build_view_filters_and_sorts
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

logger = logging.getLogger(__name__)


@method_decorator(
    name="retrieve",
    decorator=[
        has_perm_class("requires_viewer"),
        has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
    ],
)
@method_decorator(
    name="list",
    decorator=[
        has_perm_class("requires_viewer"),
        # has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
    ],
)
@method_decorator(
    name="create",
    decorator=[
        has_perm_class("requires_member"),
        has_hierarchy_access(body_ali_id="ali"),
    ],
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

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(facilities_plan_run_id_kwarg="pk")
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
        inventory_type = "property"
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

        if request.query_params.get("only_ids", "false") == "true":
            return JsonResponse({"ids": list(views.values_list("id", flat=True))})

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

        for property_json, run_info in zip(
            properties, view_run_infos[paginator.page(page).start_index() - 1 : paginator.page(page).end_index() + 1]
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

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(facilities_plan_run_id_kwarg="pk")
    @action(detail=True, methods=["POST"])
    def run(self, request, pk):
        try:
            fpr = FacilitiesPlanRun.objects.get(pk=pk)
        except (Organization.DoesNotExist, FacilitiesPlanRun.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        fpr.run()

        return JsonResponse({"status": "success"})
