"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import AccessLevelInstance, DataReport, Goal, GoalStandard, GoalTransaction, Organization
from seed.serializers.data_reports import DataReportSerializer
from seed.serializers.goals import GoalStandardSerializer, GoalTransactionSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.goals import get_or_create_goal_notes, get_portfolio_summary
from seed.utils.viewsets import ModelViewSetWithoutPatch


@method_decorator(
    name="destroy",
    decorator=[
        swagger_auto_schema_org_query_param,
        has_perm_class("requires_member"),
        has_perm_class("requires_non_leaf_access"),
        has_hierarchy_access(data_report_id_kwarg="pk"),
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
class DataReportViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = DataReportSerializer
    queryset = DataReport.objects.all()

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        data_reports = DataReport.objects.filter(
            organization=organization_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
        )
        return JsonResponse({"status": "success", "data_reports": self.serializer_class(data_reports, many=True).data})

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    def retrieve(self, request, pk):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        try:
            data_report = DataReport.objects.select_related("current_cycle").get(
                pk=pk,
                organization=organization_id,
                access_level_instance__lft__gte=access_level_instance.lft,
                access_level_instance__rgt__lte=access_level_instance.rgt,
            )
        except DataReport.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)

        data_report_data = self.serializer_class(data_report).data
        return JsonResponse({"status": "success", "data_report": data_report_data})

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_perm_class("requires_non_leaf_access")
    @has_hierarchy_access(body_ali_id="access_level_instance")
    def create(self, request):
        data = request.data
        goals = data.pop("goals")
        serializer = DataReportSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        data_report = serializer.save()
        goal_serializers = {"standard": GoalStandardSerializer, "transaction": GoalTransactionSerializer}
        errors = []
        # create_goals
        for goal_data in goals:
            goal_data["data_report"] = data_report.id
            goal_serializer = goal_serializers[data["type"]](data=goal_data)
            if goal_serializer.is_valid():
                goal_serializer.save()
            else:
                errors.append("Error creating goal")

        return JsonResponse({"status": "success", "errors": errors, "data": serializer.data}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_perm_class("requires_non_leaf_access")
    @has_hierarchy_access(data_report_id_kwarg="pk")
    def update(self, request, pk):
        try:
            data_report = DataReport.objects.get(pk=pk)
        except DataReport.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        data = request.data
        goals = data.pop("goals")
        serializer = DataReportSerializer(data_report, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data_report = serializer.save()
        goal_serializers = {GoalStandard: GoalStandardSerializer, GoalTransaction: GoalTransactionSerializer}
        errors = []
        for goal_data in goals:
            goal = Goal.objects.get(id=goal_data["id"])
            goal_serializer = goal_serializers[goal.__class__](goal, data=goal_data, partial=True)
            if goal_serializer.is_valid():
                goal_serializer.save()
            else:
                errors.append("Error Updating Goal")

        return JsonResponse({"status": "success", "erorrs": errors, "data": serializer.data})

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(data_report_id_kwarg="pk")
    @action(detail=True, methods=["GET"])
    def portfolio_summary(self, request, pk):
        """
        Gets a Portfolio Summary dictionaries for goals in a data report
        """
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            data_report = DataReport.objects.get(pk=pk)
            # goal = Goal.objects.get(pk=pk)
        except (Organization.DoesNotExist, DataReport.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        summaries = {}
        for goal in data_report.goals():
            # If new properties heave been uploaded, create goal_notes
            get_or_create_goal_notes(goal)
            summaries[goal.id] = get_portfolio_summary(org, goal)
        return JsonResponse(summaries, safe=False)
