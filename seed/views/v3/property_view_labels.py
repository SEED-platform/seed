"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import action

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import CycleGoal, PropertyViewLabel
from seed.serializers.property_view_labels import PropertyViewLabelSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch


class PropertyViewLabelViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = PropertyViewLabelSerializer
    queryset = PropertyViewLabel.objects.all()

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["GET"])
    def list_by_cycle_goal(self, request):
        """
        Return property view labels that are attached to the passed cycle and
        a. unattached to any goal
        b. or attached to the passed goal
        """
        cycle_goal_id = request.GET.get("cycle_goal_id")
        try:
            cycle_goal = CycleGoal.objects.get(id=cycle_goal_id)
        except CycleGoal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Goal does not exist"})

        pvls = PropertyViewLabel.objects.filter(
            Q(propertyview__cycle=cycle_goal.current_cycle_id) & (Q(goal=cycle_goal.goal_id) | Q(goal__isnull=True))
        )
        pvls = self.serializer_class(pvls, many=True).data

        return JsonResponse(pvls, safe=False)
