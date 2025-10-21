"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import requests
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.utils import DataError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action
from simple_salesforce import Salesforce

from seed.decorators import ajax_request_class, get_bb_salesforce_config
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import AccessLevelInstance, Column, CycleGoal, Goal, GoalNote, HistoricalNote, Organization, Property, TaxLotProperty
from seed.serializers.goals import CycleGoalSerializer, GoalSerializer
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.cache import get_cache_raw
from seed.utils.generic import get_int
from seed.utils.goal_notes import get_permission_data
from seed.utils.goals import (
    combine_properties,
    get_kbtu,
    get_or_create_goal_notes,
    get_portfolio_summary,
    get_preferred,
    get_weighted_eui_for_each_cycle_goal,
    percentage_difference,
    set_transaction_data,
)
from seed.utils.search import FilterError, build_view_filters_and_sorts, filter_views_on_related
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger(__name__)


@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_perm_class("requires_non_leaf_access"),
        has_hierarchy_access(goal_id_kwarg="pk"),
    ],
)
@method_decorator(
    name="create",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_perm_class("requires_non_leaf_access"),
        has_hierarchy_access(body_ali_id="access_level_instance"),
    ],
)
class GoalViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = GoalSerializer
    queryset = Goal.objects.all()

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        goals = Goal.objects.filter(
            organization=organization_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
        )
        return JsonResponse({"status": "success", "goals": self.serializer_class(goals, many=True).data})

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    def retrieve(self, request, pk):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        try:
            goal = Goal.objects.get(
                pk=pk,
                organization=organization_id,
                access_level_instance__lft__gte=access_level_instance.lft,
                access_level_instance__rgt__lte=access_level_instance.rgt,
            )
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)

        goal_data = self.serializer_class(goal).data

        return JsonResponse({"status": "success", "goal": goal_data})

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_perm_class("requires_non_leaf_access")
    @has_hierarchy_access(goal_id_kwarg="pk")
    def update(self, request, pk):
        try:
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        serializer = GoalSerializer(goal, data=request.data, partial=True)

        if not serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return JsonResponse(serializer.data)

    @has_perm_class("requires_member")
    @action(detail=True, methods=["PUT"])
    def bulk_update_goal_notes(self, request, pk):
        """Bulk updates Goal-related fields for a given goal and property view ids"""
        org_id = self.get_organization(request)
        try:
            goal = Goal.objects.get(pk=pk, goal__organization=org_id)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)

        property_view_ids = request.data.get("property_view_ids", [])
        properties = Property.objects.filter(views__in=property_view_ids).select_related("historical_notes")
        goal_notes = GoalNote.objects.filter(goal=goal, property__in=properties)

        data = request.data.get("data", {})

        if "historical_note" in data:
            historical_notes = HistoricalNote.objects.filter(property__in=properties)
            result = historical_notes.update(text=data["historical_note"])
            del data["historical_note"]

        if data:
            data = get_permission_data(data, request.access_level_instance_id)
            result = goal_notes.update(**data)

        return JsonResponse({"status": "success", "message": f"Updated {result} properties"})

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="pk")
    @action(detail=True, methods=["GET"])
    def get_weighted_euis(self, request, pk):
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except (Organization.DoesNotExist, Goal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        weighted_euis = get_weighted_eui_for_each_cycle_goal(org, goal)

        return JsonResponse({"status": "success", "results": weighted_euis})

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="pk")
    @action(detail=True, methods=["GET"])
    @get_bb_salesforce_config
    def salesforce_summary(self, request, pk, bb_salesforce_config):
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        cycle_goals = goal.current_cycles.all()

        # get seed side summary
        summary = {}
        for cycle_goal in cycle_goals:
            summary[cycle_goal.current_cycle.name] = {"id": cycle_goal.id, "seed": get_portfolio_summary(org, cycle_goal), "salesforce": {}}

        # get salesforce side summary
        cycle_name_by_salesforce_annual_report_id = {
            cg.salesforce_annual_report_id: cg.current_cycle.name for cg in cycle_goals if cg.salesforce_annual_report_id
        }
        stringy_list_of_salesforce_annual_report_id = ", ".join([f"'{k}'" for k in cycle_name_by_salesforce_annual_report_id])
        access_token = get_cache_raw(f"access_token_{org_id}")
        salesforce_fields = [
            "Id",
            "BB_Goal__r.BB_Other_Baseline__c",
            "BB_Goal__r.BB_BBC_Portfolio_Average_EUI_Baseline__c",
            "BB_Reporting_Year_Start_Date__c",
            "BB_Reporting_Year_End_Date__c",
            "BB_Num_of_Participating_Facilities__c",
            "BB_Portfolio_Average_EUI__c",
            "BB_Shared_Square_Feet__c",
            "BB_Reviewed_Square_Feet__c",
            "BB_Energy_IntensityImprovement_Current__c",
            "BB_Other__c",
            "BB_Total_Improvement_in_Energy_Intensity__c",
            "BB_New_Energy_Savings_for_Current_Year__c",
            "BB_Report_Status__c",
            "BB_BBC_Data_Review_Status__c",
        ]
        response = requests.get(
            f"{bb_salesforce_config.salesforce_url}/data/v64.0/query?",
            params={
                "q": f"SELECT {', '.join(salesforce_fields)} FROM Annual_Report__c WHERE Id IN ({stringy_list_of_salesforce_annual_report_id})",  # noqa: S608 no fear of sql injection as the id comes from the db, and must be an int
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=300,
        )
        # check response and handle errors
        if response.status_code != 200:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Error retrieving annual reports from salesforce: {response.status_code} {response.text}",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        for annual_report in response.json()["records"]:
            summary[cycle_name_by_salesforce_annual_report_id[annual_report["Id"]]]["salesforce"] = {
                "id": annual_report["Id"],
                "baseline_portfolio_kbtu": annual_report["BB_Goal__r"]["BB_Other_Baseline__c"],
                "baseline_portfolio_eui": annual_report["BB_Goal__r"]["BB_BBC_Portfolio_Average_EUI_Baseline__c"],
                "reporting_year_start": annual_report["BB_Reporting_Year_Start_Date__c"],
                "reporting_year_end": annual_report["BB_Reporting_Year_End_Date__c"],
                "number_of_properties": annual_report["BB_Num_of_Participating_Facilities__c"],
                "portfolio_average_eui": annual_report["BB_Portfolio_Average_EUI__c"],
                "shared_square_feet": annual_report["BB_Shared_Square_Feet__c"],
                "reviewed_square_feet": annual_report["BB_Reviewed_Square_Feet__c"],
                "ei_annual_improvement": annual_report["BB_Energy_IntensityImprovement_Current__c"],
                # "BB_Other_Type__c": annual_report["BB_Other_Type__c"],
                "portfolio_kbtu": annual_report["BB_Other__c"],
                "total_ei_improvement": annual_report["BB_Total_Improvement_in_Energy_Intensity__c"],
                "new_energy_savings": annual_report["BB_New_Energy_Savings_for_Current_Year__c"],
                "report_status": annual_report["BB_Report_Status__c"],
                "review_status": annual_report["BB_BBC_Data_Review_Status__c"]
            }

        return JsonResponse(summary)

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="pk")
    @action(detail=True, methods=["PUT"])
    @get_bb_salesforce_config
    def update_salesforce(self, request, pk, bb_salesforce_config):
        # Init a bunch of values
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        # get cycle_goals
        cycle_goal_ids = request.data.get("cycle_goal_ids", [])
        cycle_goals = CycleGoal.objects.filter(goal=goal, id__in=cycle_goal_ids)
        report_status = request.data.get("report_status")
        review_status = request.data.get("review_status")

        # ensure salesforce goal is attached
        for cycle_goal in cycle_goals:
            salesforce_annual_report_id = cycle_goal.salesforce_annual_report_id
            if salesforce_annual_report_id is None:
                return JsonResponse({"status": "error", "message": f"CycleGoal {cycle_goal.id} has no attached salesforce annual report."})

        # login
        access_token = get_cache_raw(f"access_token_{org_id}")
        sf = Salesforce(
            instance="doe-bb--kanbantest.sandbox.my.salesforce.com",
            session_id=access_token,
        )

        # update for each cycle goal
        for cycle_goal in cycle_goals:
            summary = get_portfolio_summary(org, cycle_goal)
            update_dict = {
                "BB_Reporting_Year_Start_Date__c": cycle_goal.current_cycle.start.strftime("%Y-%m-%d"),
                "BB_Reporting_Year_End_Date__c": cycle_goal.current_cycle.end.strftime("%Y-%m-%d"),
                "BB_Num_of_Participating_Facilities__c": summary["total_properties"],
                "BB_Portfolio_Average_EUI__c": summary["current_weighted_eui"],
                "BB_Shared_Square_Feet__c": summary["shared_sqft"],
                "BB_Reviewed_Square_Feet__c": summary["current_total_sqft"],
                "BB_Energy_IntensityImprovement_Current__c": summary["baseline_weighted_eui"] - summary["current_weighted_eui"],
                "BB_Other__c": summary["current_total_kbtu"],
                "BB_Total_Improvement_in_Energy_Intensity__c": summary["eui_change"],
                "BB_New_Energy_Savings_for_Current_Year__c": summary["baseline_total_kbtu"] - summary["current_total_kbtu"],
            }
            if report_status:
                update_dict["BB_Report_Status__c"] = report_status
            if review_status:
                update_dict["BB_BBC_Data_Review_Status__c"] = review_status

            sf.Annual_Report__c.update(salesforce_annual_report_id, update_dict)
            sf.Goal__c.update(
                cycle_goal.goal.salesforce_goal_id,
                {
                    "BB_Other_Baseline__c": summary["baseline_total_kbtu"],
                    "BB_BBC_Portfolio_Average_EUI_Baseline__c": summary["baseline_weighted_eui"],
                },
            )


@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_perm_class("requires_non_leaf_access"),
        has_hierarchy_access(goal_id_kwarg="goal_pk"),
    ],
)
class CycleGoalViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = CycleGoalSerializer
    queryset = CycleGoal.objects.all()

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_perm_class("requires_non_leaf_access")
    @has_hierarchy_access(goal_id_kwarg="goal_pk")
    def create(self, request, goal_pk):
        cycle_goal = CycleGoal.objects.create(
            goal_id=goal_pk,
            current_cycle_id=request.data.get("current_cycle"),
            salesforce_annual_report_id=request.data.get("salesforce_annual_report_id"),
            salesforce_annual_report_name=request.data.get("salesforce_annual_report_name"),
        )

        return JsonResponse(CycleGoalSerializer(cycle_goal).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="goal_pk")
    def list(self, request, goal_pk):
        cycle_goals = CycleGoal.objects.filter(
            goal_id=goal_pk,
        ).order_by("-current_cycle__start")
        return JsonResponse({"status": "success", "cycle_goals": self.serializer_class(cycle_goals, many=True).data})

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="goal_pk")
    @action(detail=True, methods=["GET"])
    def portfolio_summary(self, request, goal_pk, pk):
        """
        Gets a Portfolio Summary dictionary given a goal
        """
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            cycle_goal = CycleGoal.objects.get(pk=pk)
        except (Organization.DoesNotExist, CycleGoal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        # If new properties heave been uploaded, create goal_notes
        get_or_create_goal_notes(cycle_goal.goal)

        summary = get_portfolio_summary(org, cycle_goal)

        return JsonResponse(summary)

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="goal_pk")
    @action(detail=True, methods=["GET"])
    @get_bb_salesforce_config
    def salesforce_summary(self, request, goal_pk, pk, bb_salesforce_config):
        org_id = int(self.get_organization(request))
        try:
            cycle_goal = CycleGoal.objects.get(pk=pk)
        except CycleGoal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        # ensure salesforce goal is attached
        salesforce_annual_report_id = cycle_goal.salesforce_annual_report_id
        if salesforce_annual_report_id is None:
            return JsonResponse({"status": "error", "message": "No attached salesforce annual report."})

        # get annual reports
        access_token = get_cache_raw(f"access_token_{org_id}")
        salesforce_fields = [
            "BB_Goal__r.BB_Other_Baseline__c",
            "BB_Goal__r.BB_BBC_Portfolio_Average_EUI_Baseline__c",
            "BB_Reporting_Year_Start_Date__c",
            "BB_Reporting_Year_End_Date__c",
            "BB_Num_of_Participating_Facilities__c",
            "BB_Portfolio_Average_EUI__c",
            "BB_Shared_Square_Feet__c",
            "BB_Reviewed_Square_Feet__c",
            "BB_Energy_IntensityImprovement_Current__c",
            "BB_Other__c",
            "BB_Total_Improvement_in_Energy_Intensity__c",
            "BB_New_Energy_Savings_for_Current_Year__c",
        ]
        response = requests.get(
            f"{bb_salesforce_config.salesforce_url}/data/v64.0/query?",
            params={
                "q": f"SELECT {', '.join(salesforce_fields)} FROM Annual_Report__c WHERE Id = '{salesforce_annual_report_id}'",  # noqa: S608 no fear of sql injection as the id comes from the db, and must be an int
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=300,
        )
        # return response.json()
        annual_report = response.json()["records"][0]

        return JsonResponse(
            {
                "status": "success",
                "results": {
                    "baseline_portfolio_kbtu": annual_report["BB_Goal__r"]["BB_Other_Baseline__c"],
                    "baseline_portfolio_eui:": annual_report["BB_Goal__r"]["BB_BBC_Portfolio_Average_EUI_Baseline__c"],
                    "reporting_year_start": annual_report["BB_Reporting_Year_Start_Date__c"],
                    "reporting_year_end": annual_report["BB_Reporting_Year_End_Date__c"],
                    "number_of_properties": annual_report["BB_Num_of_Participating_Facilities__c"],
                    "portfolio_average_eui": annual_report["BB_Portfolio_Average_EUI__c"],
                    "shared_square_feet": annual_report["BB_Shared_Square_Feet__c"],
                    "reviewed_square_feet": annual_report["BB_Reviewed_Square_Feet__c"],
                    "ei_annual_improvement": annual_report["BB_Energy_IntensityImprovement_Current__c"],
                    # "BB_Other_Type__c": annual_report["BB_Other_Type__c"],
                    "portfolio_kbtu": annual_report["BB_Other__c"],
                    "total_ei_improvement": annual_report["BB_Total_Improvement_in_Energy_Intensity__c"],
                    "new_energy_savings": annual_report["BB_New_Energy_Savings_for_Current_Year__c"],
                },
            },
            status=status.HTTP_200_OK,
        )

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="goal_pk")
    @action(detail=True, methods=["PUT"])
    def data(self, request, goal_pk, pk):
        """
        Gets goal data for the main grid
        """
        # Init a bunch of values
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            cycle_goal = CycleGoal.objects.get(pk=pk)
            goal = cycle_goal.goal
        except (Organization.DoesNotExist, Goal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})
        page = request.data.get("page")
        per_page = request.data.get("per_page")
        baseline_first = request.data.get("baseline_first")
        access_level_instance_id = request.data.get("access_level_instance_id")
        related_model_sort = request.data.get("related_model_sort")
        inventory_type = "property"
        access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
        columns_from_database = Column.retrieve_all(
            org_id=org_id,
            inventory_type=inventory_type,
            only_used=False,
            include_related=False,
        )
        show_columns = list(Column.objects.filter(organization_id=org_id).values_list("id", flat=True))

        baseline_cycle, current_cycle = (cycle_goal.goal.baseline_cycle, cycle_goal.current_cycle)
        key1, key2 = ("baseline", "current") if baseline_first else ("current", "baseline")
        cycle1, cycle2 = (baseline_cycle, current_cycle) if baseline_first else (current_cycle, baseline_cycle)
        views1 = cycle1.propertyview_set.filter(
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).select_related("property")

        try:
            # Sorts initiated from Portfolio Summary that contain related model names (goal_note, historical_note) require custom handling
            if related_model_sort:
                views1 = filter_views_on_related(views1, cycle_goal.goal, request.query_params, cycle1)
            else:
                filters, annotations, order_by = build_view_filters_and_sorts(
                    request.query_params, columns_from_database, inventory_type, org.access_level_names
                )
                views1 = views1.annotate(**annotations).filter(filters).order_by(*order_by)
        except FilterError as e:
            return JsonResponse({"status": "error", "message": f"Error filtering: {e!s}"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return JsonResponse({"status": "error", "message": f"Error filtering: {e!s}"}, status=status.HTTP_400_BAD_REQUEST)

        # Paginate results
        paginator = Paginator(views1, per_page)
        try:
            views1 = paginator.page(page)
            page = int(page)
        except PageNotAnInteger:
            views1 = paginator.page(1)
            page = 1
        except EmptyPage:
            views1 = paginator.page(paginator.num_pages)
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

        property_ids = [v.property_id for v in views1]
        # fetch cycle 2 properties
        views2 = cycle2.propertyview_set.filter(
            property__id__in=property_ids,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        )

        properties1 = TaxLotProperty.serialize(views1, show_columns, columns_from_database, False, goal_pk)
        properties2 = TaxLotProperty.serialize(views2, show_columns, columns_from_database, False, goal_pk)
        # collapse pint quantity units to their magnitudes
        properties1 = [apply_display_unit_preferences(org, x) for x in properties1]
        properties2 = [apply_display_unit_preferences(org, x) for x in properties2]

        area_name = f"{goal.area_column.column_name}_{goal.area_column.id}"
        eui_columns = [f"{col.column_name}_{col.id}" for col in goal.eui_columns()]

        # lookup for pv.id to p.id
        property_lookup = {}
        for p in properties1 + properties2:
            property_lookup[p["property_view_id"]] = p["id"]

        properties = []
        for p1 in properties1:
            p2 = next((p for p in properties2 if p["id"] == p1["id"]), {})
            property = combine_properties(p1, p2)

            sqft1 = p1.get(area_name)
            sqft2 = p2.get(area_name) if p2 else None

            # add cycle specific and aggregated goal stats
            property[f"{key1}_cycle"] = cycle1.name
            property[f"{key2}_cycle"] = cycle2.name
            property[f"{key1}_sqft"] = get_int(sqft1)
            property[f"{key2}_sqft"] = get_int(sqft2)
            property[f"{key1}_eui"] = get_preferred(p1, eui_columns)
            property[f"{key2}_eui"] = get_preferred(p2, eui_columns)
            property["baseline_kbtu"] = get_kbtu(property, "baseline")
            property["current_kbtu"] = get_kbtu(property, "current")
            property["sqft_change"] = percentage_difference(property["current_sqft"], property["baseline_sqft"])
            property["eui_change"] = percentage_difference(property["baseline_eui"], property["current_eui"])

            if goal.type == "transaction" and goal.transactions_column:
                set_transaction_data(goal, property, p1, p2, key1, key2)

            properties.append(property)

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
                "property_lookup": property_lookup,
            }
        )
