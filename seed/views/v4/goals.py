"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import CycleGoal, Goal, PropertyView
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper


class GoalViewSet(viewsets.ViewSet, OrgMixin):
    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
            has_hierarchy_access(goal_id_kwarg="pk"),
        ]
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path=r"cycles/(?P<cycle_goal_id>[^/.]+)/property_view_ids",
    )
    def property_view_ids(self, request, pk, cycle_goal_id):
        """Return baseline view IDs for a goal cycle without serializing property data."""
        org_id = int(self.get_organization(request))
        try:
            goal = Goal.objects.select_related("access_level_instance").get(pk=pk, organization_id=org_id)
            CycleGoal.objects.get(pk=cycle_goal_id, goal=goal)
        except (Goal.DoesNotExist, CycleGoal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)

        access_level_instance = goal.access_level_instance
        property_view_ids = PropertyView.objects.filter(
            cycle_id=goal.baseline_cycle_id,
            property__organization_id=org_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).order_by("id").values_list("id", flat=True)

        return JsonResponse({"property_view_ids": list(property_view_ids)})