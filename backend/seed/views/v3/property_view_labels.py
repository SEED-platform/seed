"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import serializers
from rest_framework.decorators import action

from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.lib.superperms.orgs.permissions import get_org_id
from seed.models import Goal, PropertyView, PropertyViewLabel, StatusLabel
from seed.serializers.property_view_labels import PropertyViewLabelSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger(__name__)


# Schema only: includes the label attributes that `PropertyViewLabelSerializer.to_representation` adds
class PropertyViewLabelResponseSerializer(PropertyViewLabelSerializer):
    show_in_list = serializers.BooleanField(read_only=True)
    color = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


@extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()])
@extend_schema_view(
    list=extend_schema(responses=PropertyViewLabelResponseSerializer(many=True)),
    retrieve=extend_schema(responses=PropertyViewLabelResponseSerializer),
    create=extend_schema(responses={201: PropertyViewLabelResponseSerializer}),
    update=extend_schema(responses=PropertyViewLabelResponseSerializer),
)
@method_decorator([has_perm("requires_viewer")], name="list")
@method_decorator([has_perm("requires_viewer")], name="retrieve")
@method_decorator([has_perm("requires_member")], name="create")
@method_decorator([has_perm("requires_member")], name="update")
@method_decorator([has_perm("requires_member")], name="destroy")
class PropertyViewLabelViewSet(ModelViewSetWithoutPatch, OrgMixin):
    """API endpoint for the labels applied to the organization's property views (within the user's access level)"""

    serializer_class = PropertyViewLabelSerializer
    queryset = PropertyViewLabel.objects.all()

    def get_accessible_property_views(self):
        """Property views of the request's organization within the user's access level instance subtree"""
        ali = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        return PropertyView.objects.filter(
            property__organization_id=get_org_id(self.request),
            property__access_level_instance__lft__gte=ali.lft,
            property__access_level_instance__rgt__lte=ali.rgt,
        )

    def get_queryset(self):
        # `has_perm` sets the user's access level instance; without it (e.g., in schema generation) nothing is accessible
        if not hasattr(self.request, "access_level_instance_id"):
            return PropertyViewLabel.objects.none()
        return PropertyViewLabel.objects.filter(propertyview__in=self.get_accessible_property_views()).order_by("id")

    def get_serializer(self, *args, **kwargs):
        serializer = super().get_serializer(*args, **kwargs)
        if "data" in kwargs and isinstance(serializer, serializers.Serializer):
            # Only accept references to records the user can access
            serializer.fields["propertyview"].queryset = self.get_accessible_property_views()
            parent_org = Organization.objects.get(pk=get_org_id(self.request)).get_parent()
            serializer.fields["statuslabel"].queryset = StatusLabel.objects.filter(super_organization=parent_org)
            serializer.fields["goal"].queryset = Goal.objects.filter(organization_id=get_org_id(self.request))
        return serializer

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_integer_field("goal_id", True, "Goal ID"),
            AutoSchemaHelper.query_integer_field("cycle_id", False, "Cycle ID of the property views (no labels match when omitted)"),
        ],
        responses={200: PropertyViewLabelResponseSerializer(many=True)},
    )
    @method_decorator(
        [
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"], pagination_class=None)
    def list_by_cycle_goal(self, request):
        """
        Return property view labels that are attached to the passed cycle and
        a. unattached to any goal
        b. or attached to the passed goal

        If the goal does not exist in the organization, `{"status": "error", "message": "Goal does not exist"}` is returned instead.
        """
        goal_id = request.GET.get("goal_id")
        try:
            goal = Goal.objects.get(id=goal_id, organization_id=get_org_id(request))
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Goal does not exist"})
        cycle_id = request.GET.get("cycle_id")

        pvls = self.get_queryset().filter(Q(propertyview__cycle=cycle_id) & (Q(goal=goal) | Q(goal__isnull=True)))
        pvls = self.serializer_class(pvls, many=True).data

        return JsonResponse(pvls, safe=False)
