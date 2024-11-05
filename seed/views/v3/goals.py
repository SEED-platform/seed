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
from seed.models import AccessLevelInstance, Goal, GoalNote, HistoricalNote, Organization, Property, Column, TaxLotProperty
from seed.serializers.goals import GoalSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.goal_notes import get_permission_data
from seed.utils.goals import get_or_create_goal_notes, get_portfolio_summary
from seed.utils.viewsets import ModelViewSetWithoutPatch
from seed.utils.search import FilterError, build_related_model_filters_and_sorts, build_view_filters_and_sorts
from django.http import QueryDict
from pint import Quantity
from seed.serializers.pint import apply_display_unit_preferences



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
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except (Organization.DoesNotExist, Goal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})

        # If new properties heave been uploaded, create goal_notes
        get_or_create_goal_notes(goal)

        summary = get_portfolio_summary(org, goal)
        return JsonResponse(summary)

    @has_perm_class("requires_member")
    @action(detail=True, methods=["PUT"])
    def bulk_update_goal_notes(self, request, pk):
        """Bulk updates Goal-related fields for a given goal and property view ids"""
        org_id = self.get_organization(request)
        try:
            goal = Goal.objects.get(pk=pk, organization=org_id)
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
    @action(detail=True, methods=["PUT"])
    def formatted_grid_data(self, request, pk):
        """
        Gets goal data for the main grid
        """
        # Init a bunch of values
        org_id = int(self.get_organization(request))
        try:
            org = Organization.objects.get(pk=org_id)
            goal = Goal.objects.get(pk=pk)
        except (Organization.DoesNotExist, Goal.DoesNotExist):
            return JsonResponse({"status": "error", "message": "No such resource."})
        page = request.data.get("page")
        per_page = request.data.get("per_page")
        baseline_first = request.data.get("baseline_first")
        access_level_instance_id = request.data.get("access_level_instance_id")
        filters = request.data.get("filters")
        sorts = request.data.get("sorts")
        related_model_sort = request.data.get("related_model_sort")
        inventory_type = "property"
        access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
        columns_from_database = Column.retrieve_all(
            org_id=org_id,
            inventory_type=inventory_type,
            only_used=False,
            include_related=False,
        )
        # need metric 1
        # need metric 2
        show_columns = list(Column.objects.filter(organization_id=org_id).values_list("id", flat=True))

        filters_dict = QueryDict(mutable=True)
        # gonna have to figure out filters/sorts 
        # ex: { 
        #   site_eui_56__lt: 115,
        #   order_by: ["site_eui_56"]
        # }
        # filters_dict["order_by"] = []
        # filters_dict["filters"] = 
        key1, key2 = ("baseline", "current") if baseline_first else ("current", "baseline")
        
        cycle1 = getattr(goal, f"{key1}_cycle")
        cycle2 = getattr(goal, f"{key2}_cycle")
        # limit to ALI
        views1 = cycle1.propertyview_set.filter(
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        )

        try:
        # Sorts initiated from Portfolio Summary that contain related model names (goal_note, historical_note) require custom handling
            if related_model_sort:
                filters, annotations, order_by = build_related_model_filters_and_sorts(filters_dict, columns_from_database)
            else:
                filters, annotations, order_by = build_view_filters_and_sorts(
                    filters_dict, columns_from_database, inventory_type, org.access_level_names
                )
        except FilterError as e:
            return JsonResponse({"status": "error", "message": f"Error filtering: {e!s}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            views1 = views1.annotate(**annotations).filter(filters).order_by(*order_by)
        except ValueError as e:
            return JsonResponse({"status": "error", "message": f"Error filtering: {e!s}"}, status=status.HTTP_400_BAD_REQUEST)

        # fetch cycle 2 properties
        property_ids = views1.values_list('property__id')
        views2 = cycle2.propertyview_set.filter(
            property__id__in=property_ids,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        )

        properties1 = TaxLotProperty.serialize(views1, show_columns, columns_from_database, False, pk)
        properties2 = TaxLotProperty.serialize(views2, show_columns, columns_from_database, False, pk)
        # collapse pint Qunatity units to their magnitudes
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
            p2 = next((p for p in properties2 if p["id"] == p1["id"]), None)
            property = combine_properties(p1, p2)

            sqft1 = p1.get(area_name)
            sqft2 = p2.get(area_name) if p2 else None 
            
            # add cycle specific and aggregated goal stats
            property[f"{key1}_cycle"] = cycle1.name 
            property[f"{key2}_cycle"] = cycle2.name
            property[f"{key1}_sqft"] = convert_quantity(sqft1)
            property[f"{key2}_sqft"] = convert_quantity(sqft2)
            property[f"{key1}_eui"] = get_preferred(p1, eui_columns)
            property[f"{key2}_eui"] = get_preferred(p2, eui_columns)
            property["baseline_kbtu"] = get_kbtu(property, "baseline")
            property["current_kbtu"] = get_kbtu(property, "current")
            property["sqft_change"] = percentage(property["current_sqft"], property["baseline_sqft"])
            property["eui_change"] = percentage(property["baseline_eui"], property["current_eui"])

            properties.append(property)
        # UNIT ERRORS, need to convert quantity to number
        # not mine, but others. check taxlot property serialize unit conversion.
        # SHOULD REALLY HAVE A SHORT LIST OF COLUMNS

        results = {
            "properties": properties,
            "property_lookup": property_lookup
        }

        # PAGINATION
        # FILTERS

        return JsonResponse({"status": "success", "data": results})
    
def combine_properties(p1, p2):
    if not p2:
        return p1
    combined = p1.copy()
    for key, value in p2.items():
        if value is not None:
            combined[key] = value 
    return combined

def percentage(a, b):
    if not a or b is None:
        return None
    value = round(((a - b) / a) * 100)
    return None if value != value else value  # value != value to check for NaN

def get_preferred(p, columns):
    if not p:
        return
    for col in columns:
        return convert_quantity(p[col])

        
def convert_quantity(value):
    if isinstance(value, Quantity):
        value = value.m
    return value


def get_kbtu(property, key):
    if property[f"{key}_sqft"] is not None and property[f"{key}_eui"] is not None:
        return round(property[f"{key}_sqft"] * property[f"{key}_eui"])