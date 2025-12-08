"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework.decorators import action

from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Goal, PropertyViewLabel
from seed.serializers.property_view_labels import PropertyViewLabelSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger()


class PropertyViewLabelViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = PropertyViewLabelSerializer
    queryset = PropertyViewLabel.objects.all()

    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def list_by_goal(self, request):
        """
        Return property view labels that are attached to the passed cycle and
        a. unattached to any goal
        b. or attached to the passed goal
        """
        goal_id = request.GET.get("goal_id")
        try:
            goal = Goal.objects.get(id=goal_id)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Goal does not exist"})
        cycle_id = request.GET.get("cycle_id")

        pvls = PropertyViewLabel.objects.filter(Q(propertyview__cycle=cycle_id) & (Q(goal=goal) | Q(goal__isnull=True)))
        pvls = self.serializer_class(pvls, many=True).data

        return JsonResponse(pvls, safe=False)
