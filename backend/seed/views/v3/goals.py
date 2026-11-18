"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import requests
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.utils import DataError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_serializer, extend_schema_view
from rest_framework import serializers, status
from rest_framework.decorators import action
from simple_salesforce import Salesforce

from seed.decorators import ajax_request, get_bb_salesforce_config
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import (
    AccessLevelInstance,
    Column,
    Cycle,
    CycleGoal,
    Goal,
    GoalNote,
    HistoricalNote,
    Organization,
    Property,
    TaxLotProperty,
)
from seed.serializers.cycles import CycleSerializer
from seed.serializers.goals import CycleGoalSerializer, GoalSerializer
from seed.serializers.pint import apply_display_unit_preferences
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
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


class GoalResponseSerializer(GoalSerializer):
    """Documents a goal as represented, including the fields added by `GoalSerializer.to_representation`"""

    level_name_index = serializers.IntegerField()
    level_name = serializers.CharField()
    baseline_cycle_name = serializers.CharField()
    eui_column1_name = serializers.CharField(allow_null=True)
    eui_column2_name = serializers.CharField(allow_null=True)
    eui_column3_name = serializers.CharField(allow_null=True)
    area_column_name = serializers.CharField(allow_null=True)
    transactions_column_name = serializers.CharField(allow_null=True, required=False, help_text="Only included for transaction goals")
    partner_note_approval_user_name = serializers.CharField(
        required=False, help_text="Only included when `partner_note_approval_user` is set"
    )


@extend_schema_serializer(many=False)
class GoalListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    goals = GoalResponseSerializer(many=True)


class GoalDetailResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    goal = GoalResponseSerializer()


class CycleGoalResponseSerializer(CycleGoalSerializer):
    """Documents a cycle goal as represented, with its current cycle expanded"""

    current_cycle = CycleSerializer()


@extend_schema_serializer(many=False)
class CycleGoalListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    cycle_goals = CycleGoalResponseSerializer(many=True)


# org from the request body's `organization` (see `get_org_id`), which the frontend sends instead
body_or_query_org_id_field = AutoSchemaHelper.query_org_id_field(
    required=False, description="Organization ID; required unless `organization` is in the request body"
)

portfolio_summary_schema = AutoSchemaHelper.schema_factory(
    {
        "total_properties": "integer",
        "shared_sqft": "number",
        "total_passing": "integer",
        "total_new_or_acquired": "integer",
        "passing_committed": "integer",
        "passing_shared": "integer",
        "baseline_cycle_name": "string",
        "baseline_total_sqft": "number",
        "baseline_total_kbtu": "integer",
        "baseline_weighted_eui": "integer",
        "current_cycle_name": "string",
        "current_total_sqft": "number",
        "current_total_kbtu": "integer",
        "current_weighted_eui": "integer",
        "sqft_change": "integer",
        "eui_change": "integer",
        "baseline_total_transactions": "integer",
        "baseline_weighted_eui_t": "integer",
        "current_total_transactions": "integer",
        "current_weighted_eui_t": "integer",
        "transactions_change": "integer",
        "eui_t_change": "integer",
    },
    description="Portfolio summary of a cycle goal's baseline and current cycles. Values that cannot be calculated are null, and the "
    "transaction fields (`*_transactions`, `*_eui_t`, `transactions_change`, and `eui_t_change`) are only included for transaction goals.",
)

salesforce_annual_report_fields = {
    "baseline_portfolio_kbtu": "number",
    "reporting_year_start": "date",
    "reporting_year_end": "date",
    "number_of_properties": "number",
    "portfolio_average_eui": "number",
    "shared_square_feet": "number",
    "reviewed_square_feet": "number",
    "ei_annual_improvement": "number",
    "portfolio_kbtu": "number",
    "total_ei_improvement": "number",
    "new_energy_savings": "number",
}

salesforce_config_error_description = (
    "If the organization's BB Salesforce connection is missing or incomplete, "
    'the response is `{"status": "error", "valid": false, "response": "<message>"}` (also with HTTP 200).'
)

salesforce_update_response_description = (
    "The body is `null` on success. Errors (e.g., an unknown cycle goal, or one without a Salesforce annual report) "
    'are returned as `{"status": "error", "message": "<message>"}` with HTTP 200, or HTTP 500 if Salesforce fails. '
    + salesforce_config_error_description
)


@extend_schema_org_query_param
@extend_schema_view(
    create=extend_schema(parameters=[body_or_query_org_id_field], responses={201: GoalResponseSerializer}),
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_perm("requires_non_leaf_access"),
        has_hierarchy_access(goal_id_kwarg="pk"),
    ],
    name="destroy",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_perm("requires_non_leaf_access"),
        has_hierarchy_access(body_ali_id="access_level_instance"),
    ],
    name="create",
)
class GoalViewSet(ModelViewSetWithoutPatch, OrgMixin):
    """Goals to reduce the weighted EUI of the properties in an access level instance, relative to a baseline cycle"""

    serializer_class = GoalSerializer
    queryset = Goal.objects.all()
    pagination_class = None

    @extend_schema(responses=GoalListResponseSerializer)
    @method_decorator(
        [
            has_perm("requires_viewer"),
        ]
    )
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        goals = Goal.objects.filter(
            organization=organization_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
        )
        return JsonResponse({"status": "success", "goals": self.serializer_class(goals, many=True).data})

    @extend_schema(responses=GoalDetailResponseSerializer)
    @method_decorator(
        [
            has_perm("requires_viewer"),
        ]
    )
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

    @extend_schema(
        parameters=[body_or_query_org_id_field],
        request=GoalSerializer(partial=True),
        responses=GoalResponseSerializer,
    )
    @method_decorator(
        [
            has_perm("requires_member"),
            has_perm("requires_non_leaf_access"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ]
    )
    def update(self, request, pk):
        """Partially updates a goal (only the given fields are changed)"""
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

    @extend_schema(responses={200: portfolio_summary_schema})
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def portfolio_summary(self, request, pk):
        """
        Gets a Portfolio Summary dictionary given a goal
        """
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except (Organization.DoesNotExist, Goal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        # If new properties heave been uploaded, create goal_notes
        get_or_create_goal_notes(goal)

        summary = get_portfolio_summary(org, goal)
        return JsonResponse(summary)

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {
                "property_view_ids": ["integer"],
                "data": {
                    "question": "string",
                    "resolution": "string",
                    "passed_checks": "boolean",
                    "new_or_acquired": "boolean",
                    "historical_note": "string",
                },
            }
        ),
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "message": "string"})},
    )
    @method_decorator(
        [
            has_perm("requires_member"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    def bulk_update_goal_notes(self, request, pk):
        """Bulk updates Goal-related fields for a given goal and property view ids

        `data` holds the goal note fields to set (`question`, `resolution`, `passed_checks`, and `new_or_acquired`; other keys
        are ignored), plus `historical_note` to set the properties' historical note text.
        Users at a leaf access level may only update `resolution` (and `historical_note`).
        """
        org_id = self.get_organization(request)
        try:
            goal = Goal.objects.get(pk=pk, organization=org_id)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)

        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        property_view_ids = request.data.get("property_view_ids", [])
        properties = Property.objects.filter(
            organization_id=org_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
            views__in=property_view_ids,
        ).select_related("historical_notes")
        goal_notes = GoalNote.objects.filter(goal=goal, property__in=properties)

        data = request.data.get("data", {})
        result = 0

        if "historical_note" in data:
            historical_notes = HistoricalNote.objects.filter(property__in=properties)
            result = historical_notes.update(text=data["historical_note"])

        # only the goal note fields the user may update (so not `historical_note`)
        data = get_permission_data(data, request.access_level_instance_id)
        if data:
            result = goal_notes.update(**data)

        return JsonResponse({"status": "success", "message": f"Updated {result} properties"})

    @extend_schema(
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "results": [
                        {
                            "Cycle Name": "string",
                            "Baseline?": "integer",
                            "EUI": "integer",
                            "Goal": "number",
                            "Annual % Imp": "number",
                            "Cumulative % Imp": "number",
                        }
                    ],
                },
                description="`results` starts with the baseline cycle, followed by each cycle goal in chronological order. "
                "It is empty if the baseline weighted EUI cannot be calculated.",
            )
        }
    )
    @method_decorator(
        [
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ],
    )
    @action(detail=True, methods=["GET"])
    def get_weighted_euis(self, request, pk):
        """Gets the weighted EUI of the goal's baseline cycle and each of its cycle goals"""
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except (Organization.DoesNotExist, Goal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        weighted_euis = get_weighted_eui_for_each_cycle_goal(org, goal)

        return JsonResponse({"status": "success", "results": weighted_euis})

    @extend_schema(
        responses={
            200: OpenApiResponse(
                {
                    "type": "object",
                    "description": "Keyed by the name of each cycle goal's current cycle",
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "description": "Cycle goal ID"},
                            "seed": portfolio_summary_schema,
                            "salesforce": AutoSchemaHelper.schema_factory(
                                {
                                    "id": "string",
                                    "baseline_portfolio_eui": "number",
                                    **salesforce_annual_report_fields,
                                    "report_status": "string",
                                    "review_status": "string",
                                },
                                description="The cycle goal's Salesforce annual report; empty if none is attached",
                            ),
                        },
                    },
                },
                description=salesforce_config_error_description,
            )
        }
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ],
    )
    @action(detail=True, methods=["GET"])
    @get_bb_salesforce_config
    def salesforce_summary(self, request, pk, bb_salesforce_config):
        """Compares the SEED portfolio summary of each of the goal's cycle goals with its Salesforce annual report"""
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
                "review_status": annual_report["BB_BBC_Data_Review_Status__c"],
            }

        return JsonResponse(summary)

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {"cycle_goal_id": "integer", "report_status": "string", "review_status": "string"},
            required=["cycle_goal_id"],
        ),
        responses={200: OpenApiResponse(description=salesforce_update_response_description)},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_perm("requires_non_leaf_access"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    @get_bb_salesforce_config
    def update_salesforce_current(self, request, pk, bb_salesforce_config):
        """Updates the Salesforce annual report of a cycle goal, and the Salesforce goal, with the SEED portfolio summary

        `report_status` and `review_status` optionally set the annual report's statuses.
        """
        # Init a bunch of values
        report_status = request.data.get("report_status")
        review_status = request.data.get("review_status")
        cycle_goal_id = request.data.get("cycle_goal_id", None)
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        # get cycle_goal and ensure salesforce goal is attached
        cycle_goal = CycleGoal.objects.filter(goal=goal, id=cycle_goal_id).first()
        if cycle_goal is None:
            return JsonResponse({"status": "error", "message": "No such resource."})
        if cycle_goal.salesforce_annual_report_id is None:
            return JsonResponse({"status": "error", "message": f"CycleGoal {cycle_goal.id} has no attached salesforce annual report."})

        # login
        access_token = get_cache_raw(f"access_token_{org_id}")
        try:
            sf = Salesforce(
                instance_url=bb_salesforce_config.salesforce_url,
                session_id=access_token,
            )
        except Exception as e:
            logger.error(f"Error connecting to Salesforce: {e}")
            return JsonResponse(
                {"status": "error", "message": "Error connecting to Salesforce."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # update cycle goal
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

        try:
            sf.Annual_Report__c.update(cycle_goal.salesforce_annual_report_id, update_dict)
        except Exception as e:
            logger.error(f"Error updating Salesforce Annual Report {cycle_goal.salesforce_annual_report_name}: {e}")
            return JsonResponse(
                {"status": "error", "message": f"Error updating Salesforce Annual Report {cycle_goal.salesforce_annual_report_name}."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        # TODO: this should ONLY happen when we are updating the current report.
        try:
            sf.Goal__c.update(
                cycle_goal.goal.salesforce_goal_id,
                {
                    "BB_Other_Baseline__c": summary["baseline_total_kbtu"],
                    "BB_BBC_Portfolio_Average_EUI_Baseline__c": summary["baseline_weighted_eui"],
                },
            )
        except Exception as e:
            logger.error(f"Error updating Salesforce Goal {cycle_goal.goal.salesforce_goal_name}: {e}")
            return JsonResponse(
                {"status": "error", "message": f"Error updating Salesforce Goal {cycle_goal.goal.salesforce_goal_name}."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        request=AutoSchemaHelper.json_body({"cycle_goal_ids": ["integer"]}),
        responses={200: OpenApiResponse(description=salesforce_update_response_description)},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_member"),
            has_perm("requires_non_leaf_access"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["PUT"])
    @get_bb_salesforce_config
    def update_salesforce_historical(self, request, pk, bb_salesforce_config):
        """Updates the Salesforce annual reports of past cycle goals with their SEED portfolio summaries"""
        # Init a bunch of values
        cycle_goal_ids = request.data.get("cycle_goal_ids", [])
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        # get cycle_goals and ensure salesforce goal is attached
        cycle_goals = CycleGoal.objects.filter(goal=goal, id__in=cycle_goal_ids)
        for cycle_goal in cycle_goals:
            salesforce_annual_report_id = cycle_goal.salesforce_annual_report_id
            if salesforce_annual_report_id is None:
                return JsonResponse({"status": "error", "message": f"CycleGoal {cycle_goal.id} has no attached salesforce annual report."})

        # login
        access_token = get_cache_raw(f"access_token_{org_id}")
        try:
            sf = Salesforce(
                instance_url=bb_salesforce_config.salesforce_url,
                session_id=access_token,
            )
        except Exception as e:
            logger.error(f"Error connecting to Salesforce: {e}")
            return JsonResponse(
                {"status": "error", "message": "Error connecting to Salesforce."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # update for each cycle goal
        for cycle_goal in cycle_goals:
            summary = get_portfolio_summary(org, cycle_goal)
            update_dict = {
                "BB_Portfolio_Average_EUI__c": summary["current_weighted_eui"],
                "BB_Energy_IntensityImprovement_Current__c": summary["baseline_weighted_eui"] - summary["current_weighted_eui"],
                "BB_Other__c": summary["current_total_kbtu"],
                "BB_New_Energy_Savings_for_Current_Year__c": summary["baseline_total_kbtu"] - summary["current_total_kbtu"],
            }
            try:
                sf.Annual_Report__c.update(cycle_goal.salesforce_annual_report_id, update_dict)
            except Exception as e:
                logger.error(f"Error updating Salesforce Annual Report {cycle_goal.salesforce_annual_report_name}: {e}")
                return JsonResponse(
                    {"status": "error", "message": f"Error updating Salesforce Annual Report {cycle_goal.salesforce_annual_report_name}."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


@extend_schema_org_query_param
@extend_schema_view(
    retrieve=extend_schema(responses=CycleGoalResponseSerializer),
    update=extend_schema(responses=CycleGoalResponseSerializer),
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(goal_id_kwarg="goal_pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_perm("requires_non_leaf_access"),
        has_hierarchy_access(goal_id_kwarg="goal_pk"),
    ],
    name="update",
)
@method_decorator(
    name="destroy",
    decorator=[
        has_perm("requires_member"),
        has_perm("requires_non_leaf_access"),
        has_hierarchy_access(goal_id_kwarg="goal_pk"),
    ],
)
class CycleGoalViewSet(ModelViewSetWithoutPatch, OrgMixin):
    """The cycles whose properties are compared against a goal's baseline cycle"""

    serializer_class = CycleGoalSerializer
    queryset = CycleGoal.objects.all()
    pagination_class = None

    def get_queryset(self):
        # a cycle goal is only accessible through its own goal, whose access is checked by `has_hierarchy_access`
        return CycleGoal.objects.filter(goal_id=self.kwargs.get("goal_pk"))

    @extend_schema(responses={201: CycleGoalResponseSerializer})
    @method_decorator(
        [
            has_perm("requires_member"),
            has_perm("requires_non_leaf_access"),
            has_hierarchy_access(goal_id_kwarg="goal_pk"),
        ],
    )
    def create(self, request, goal_pk):
        goal = Goal.objects.get(pk=goal_pk)
        current_cycle_id = request.data.get("current_cycle")
        if not Cycle.objects.filter(pk=current_cycle_id, organization_id=goal.organization_id).exists():
            return JsonResponse({"status": "error", "message": "No such cycle."}, status=status.HTTP_400_BAD_REQUEST)
        cycle_goal = CycleGoal.objects.create(
            goal=goal,
            current_cycle_id=current_cycle_id,
            salesforce_annual_report_id=request.data.get("salesforce_annual_report_id"),
            salesforce_annual_report_name=request.data.get("salesforce_annual_report_name"),
        )

        return JsonResponse(CycleGoalSerializer(cycle_goal).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses=CycleGoalListResponseSerializer)
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="goal_pk"),
        ],
    )
    def list(self, request, goal_pk):
        cycle_goals = CycleGoal.objects.filter(
            goal_id=goal_pk,
        ).order_by("-current_cycle__start")
        return JsonResponse({"status": "success", "cycle_goals": self.serializer_class(cycle_goals, many=True).data})

    @extend_schema(responses={200: portfolio_summary_schema})
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="goal_pk"),
        ],
    )
    @action(detail=True, methods=["GET"])
    def portfolio_summary(self, request, goal_pk, pk):
        """
        Gets a Portfolio Summary dictionary given a cycle goal
        """
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            cycle_goal = CycleGoal.objects.get(pk=pk, goal=goal_pk)
        except (Organization.DoesNotExist, CycleGoal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        # If new properties heave been uploaded, create goal_notes
        get_or_create_goal_notes(cycle_goal.goal)

        summary = get_portfolio_summary(org, cycle_goal)

        return JsonResponse(summary)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                AutoSchemaHelper.schema_factory(
                    {"status": "string", "results": {"baseline_portfolio_eui:": "number", **salesforce_annual_report_fields}}
                ),
                description="The cycle goal's Salesforce annual report. If no annual report is attached, the response is "
                '`{"status": "error", "message": "<message>"}` (also with HTTP 200). ' + salesforce_config_error_description,
            )
        }
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="goal_pk"),
        ],
    )
    @action(detail=True, methods=["GET"])
    @get_bb_salesforce_config
    def salesforce_summary(self, request, goal_pk, pk, bb_salesforce_config):
        """Gets the Salesforce annual report attached to a cycle goal"""
        org_id = int(self.get_organization(request))
        try:
            cycle_goal = CycleGoal.objects.get(pk=pk, goal=goal_pk)
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

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_array_field(
                "order_by",
                required=False,
                description="Column names to sort by, prefixed with `-` for descending order",
                item_type="string",
            ),
        ],
        request=AutoSchemaHelper.json_body(
            {
                "page": "integer",
                "per_page": "integer",
                "baseline_first": "boolean",
                "access_level_instance_id": "integer",
                "related_model_sort": "boolean",
            },
            required=["per_page", "access_level_instance_id"],
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "pagination": {
                        "page": "integer",
                        "start": "integer",
                        "end": "integer",
                        "num_pages": "integer",
                        "has_next": "boolean",
                        "has_previous": "boolean",
                        "total": "integer",
                    },
                    "properties": ["object"],
                    "property_lookup": "object",
                },
                description="`properties` combines each property's baseline and current cycle data with its goal statistics, "
                "and `property_lookup` maps property view IDs to property IDs",
            )
        },
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="goal_pk"),
        ],
    )
    @action(detail=True, methods=["PUT"])
    def data(self, request, goal_pk, pk):
        """
        Gets goal data for the main grid

        The properties are those in the `access_level_instance_id` subtree, filtered by column name query parameters
        (e.g., `?site_eui__gte=100`) and sorted by `order_by`.
        """
        # Init a bunch of values
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            cycle_goal = CycleGoal.objects.get(pk=pk, goal=goal_pk)
            goal = cycle_goal.goal
        except (Organization.DoesNotExist, CycleGoal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)
        page = request.data.get("page")
        per_page = request.data.get("per_page")
        baseline_first = request.data.get("baseline_first")
        access_level_instance_id = request.data.get("access_level_instance_id")
        related_model_sort = request.data.get("related_model_sort")
        inventory_type = "property"
        user_access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        try:
            # only properties within the user's access level instance subtree may be returned
            access_level_instance = AccessLevelInstance.objects.get(
                pk=access_level_instance_id,
                organization_id=org_id,
                lft__gte=user_access_level_instance.lft,
                rgt__lte=user_access_level_instance.rgt,
            )
        except AccessLevelInstance.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)
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
        views1 = (
            cycle1.propertyview_set.filter(
                property__organization_id=org_id,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )
            .select_related("property")
            .order_by("id")
        )

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
            property[f"{key1}_view_id"] = p1["property_view_id"]
            property[f"{key2}_view_id"] = p2.get("property_view_id", None)
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
