"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db.models import F, Sum
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from quantityfield.units import ureg
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.models import AccessLevelInstance, Goal, GoalNote, HistoricalNote, Organization, Property, PropertyView
from seed.serializers.goals import GoalSerializer
from seed.serializers.pint import collapse_unit
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.goals import get_area_expression, get_eui_expression, get_or_create_goal_notes, percentage
from seed.utils.goal_notes import get_permission_data
from seed.utils.viewsets import ModelViewSetWithoutPatch


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
            goal = Goal.objects.select_related("current_cycle").get(
                pk=pk,
                organization=organization_id,
                access_level_instance__lft__gte=access_level_instance.lft,
                access_level_instance__rgt__lte=access_level_instance.rgt,
            )
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)
        
        goal_data = self.serializer_class(goal).data 
        property_view_ids = goal.current_cycle.propertyview_set.all().values_list("id", flat=True)
        goal_data["current_cycle_property_view_ids"] = list(property_view_ids)
        
        return JsonResponse({"status": "success", "goal": goal_data})

    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_member")
    @has_perm_class("requires_non_leaf_access")
    @has_hierarchy_access(goal_id_kwarg="pk")
    def update(self, request, pk):
        try:
            goal = Goal.objects.get(pk=pk)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "errors": "No such resource."})

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

    @ajax_request_class
    @swagger_auto_schema_org_query_param
    @has_perm_class("requires_viewer")
    @has_hierarchy_access(goal_id_kwarg="pk")
    @action(detail=True, methods=["GET"])
    def portfolio_summary(self, request, pk):
        """
        Gets a Portfolio Summary dictionary given a goal
        """
        org_id = int(self.get_organization(request))
        org = Organization.objects.get(pk=org_id)
        goal = Goal.objects.get(pk=pk)
        summary = {"total_properties": goal.current_cycle.propertyview_set.count()}

        # If new properties heave been uploaded, create goal_notes
        get_or_create_goal_notes(goal)

        for current, cycle in enumerate([goal.baseline_cycle, goal.current_cycle]):
            # Return all properties
            property_views = PropertyView.objects.select_related("property", "state").filter(
                property__organization_id=org_id,
                cycle_id=cycle.id,
                property__access_level_instance__lft__gte=goal.access_level_instance.lft,
                property__access_level_instance__rgt__lte=goal.access_level_instance.rgt,
                property__goalnote__goal__id=goal.id,
            )
            # Shared area is area of all properties regardless of valid status
            property_views = property_views.annotate(area=get_area_expression(goal))
            if current:
                summary["shared_sqft"] = property_views.aggregate(shared_sqft=Sum("area"))["shared_sqft"]
                summary["total_passing"] = GoalNote.objects.filter(goal=goal, passed_checks=True).count()
                summary["total_new_or_acquired"] = GoalNote.objects.filter(goal=goal, new_or_acquired=True).count()

            # Remaining Calcs are restricted to passing checks and not new/acquired
            # use goal notes relation to properties to get valid properties views
            valid_property_ids = GoalNote.objects.filter(
                goal=goal,
                passed_checks=True,
                new_or_acquired=False
            ).values_list("property__id", flat=True)
            property_views = property_views.filter(property__id__in=valid_property_ids)

            # Create annotations for kbtu calcs. "eui" is based on goal column priority
            property_views = property_views.annotate(
                eui=get_eui_expression(goal),
            ).annotate(kbtu=F("eui") * F("area"))

            aggregated_data = property_views.aggregate(total_kbtu=Sum("kbtu"), total_sqft=Sum("area"))
            total_kbtu = aggregated_data["total_kbtu"]
            total_sqft = aggregated_data["total_sqft"]

            if current:
                summary["passing_committed"] = percentage(goal.commitment_sqft, total_sqft)
                summary["passing_shared"] = percentage(summary["shared_sqft"], total_sqft)

            if total_kbtu:
                total_kbtu = int(total_kbtu)

            if total_kbtu is not None and total_sqft:
                # apply units for potential unit conversion (no org setting for type ktbu so it is ignored)
                total_sqft = total_sqft * ureg("ft**2")
                weighted_eui = total_kbtu * ureg("kBtu/year") / total_sqft
                weighted_eui = int(collapse_unit(org, weighted_eui))
            else:
                weighted_eui = None

            if total_sqft is not None:
                total_sqft = collapse_unit(org, total_sqft)

            cycle_type = "current" if current else "baseline"

            summary[cycle_type] = {
                "cycle_name": cycle.name,
                "total_sqft": total_sqft,
                "total_kbtu": total_kbtu,
                "weighted_eui": weighted_eui,
            }

        summary["sqft_change"] = percentage(summary["current"]["total_sqft"], summary["baseline"]["total_sqft"])
        summary["eui_change"] = percentage(summary["baseline"]["weighted_eui"], summary["current"]["weighted_eui"])

        return summary
    
    @has_perm_class("requires_member")
    @action(detail=True, methods=["PUT"])
    def bulk_update_goal_notes(self, request, pk):
        """Bulk updates GoalNotes for a given goal and property view ids"""
        org_id = self.get_organization(request)
        try:
            goal = Goal.objects.get(pk=pk, organization=org_id)
        except Goal.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."}, status=404)
        
        property_view_ids = request.data.get('property_view_ids', [])
        properties = Property.objects.filter(views__in=property_view_ids).select_related('historical_notes')
        goal_notes = GoalNote.objects.filter(goal=goal, property__in=properties)

        data = request.data.get('data', {})

        if "historical_note" in data:
            historical_notes = HistoricalNote.objects.filter(property__in=properties)  
            result = historical_notes.update(text=data["historical_note"])
            del data['historical_note']

        if data:
            data = get_permission_data(data, request.access_level_instance_id)
            result = goal_notes.update(**data)

        return JsonResponse({"status": "success", "message": f"Updated {result} GoalNotes"})