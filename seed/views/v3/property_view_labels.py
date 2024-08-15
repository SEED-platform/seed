"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db.models import Q
from django.http import JsonResponse
from rest_framework.decorators import action

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Goal, PropertyViewLabel
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
    def list_by_goal(self, request):
        """
        Return property view labels that are attatched to the passed cycle and
        a. unattatched to any goal
        b. or attatched to the passed goal
        """
        goal_id = request.GET.get("goal_id")
        try:
            goal = Goal.objects.get(id=goal_id)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Goal does not exist"})
        cycle = request.GET.get("cycle")
        if cycle == "baseline":
            cycle = goal.baseline_cycle
        elif cycle == "current":
            cycle = goal.current_cycle
        else:
            return JsonResponse({"stutus": "error", "message": "invalid cycle, must be 'baseline' or 'current'"})
        pvls = PropertyViewLabel.objects.filter(Q(propertyview__cycle=cycle) & (Q(goal=goal_id) | Q(goal__isnull=True)))
        pvls = self.serializer_class(pvls, many=True).data

        return JsonResponse(pvls, safe=False)
