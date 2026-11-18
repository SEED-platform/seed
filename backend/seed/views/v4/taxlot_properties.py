"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Cycle
from seed.serializers.tax_lot_properties import TaxLotPropertySerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.v4.inventory_filter import InventoryFilter


class TaxLotPropertyViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin):
    serializer_class = TaxLotPropertySerializer

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_enum_field("inventory_type", "property or taxlot", ["property", "taxlot"]),
            AutoSchemaHelper.query_integer_field(
                "cycle",
                required=False,
                description="The ID of the cycle to get records from (defaults to the organization's first cycle by name)",
            ),
            AutoSchemaHelper.query_integer_field("per_page", required=False, description="Number of records per page (defaults to 100)"),
            AutoSchemaHelper.query_integer_field("page", required=False, description="Page to fetch (defaults to 1)"),
            AutoSchemaHelper.query_integer_field(
                "profile_id",
                required=False,
                description="The ID of the column list profile to use (takes precedence over the request body)",
            ),
            AutoSchemaHelper.query_string_field(
                "shown_column_ids",
                required=False,
                description="Comma-separated IDs of the columns to return (mutually exclusive with profile_id)",
            ),
            AutoSchemaHelper.query_boolean_field(
                "include_related",
                required=False,
                description="If False, related data (e.g., Tax Lot data for properties) is not added to the response (default is True)",
            ),
            AutoSchemaHelper.query_boolean_field(
                "ids_only", required=False, description="Function will return a list of view ids instead of records"
            ),
        ],
        request=AutoSchemaHelper.json_body(
            {
                "profile_id": "integer",
                "filters": "object",
                "sorts": ["string"],
                "include_view_ids": ["integer"],
                "exclude_view_ids": ["integer"],
                "include_property_ids": ["integer"],
                "access_level_instance_id": "integer",
            },
            description="Properties:\n"
            "- profile_id: Either an id of a list settings profile, or undefined (the profile_id query parameter takes precedence)\n"
            "- filters: AG Grid filter models keyed by column name with its ID suffix (e.g., `address_line_1_12`), "
            "or by access level name\n"
            "- sorts: Column names with their ID suffix to sort by, prefixed with `-` for descending order\n"
            "- include_view_ids: Only return these view IDs\n"
            "- exclude_view_ids: Exclude these view IDs\n"
            "- include_property_ids: Only return the views of these properties (property inventory only)\n"
            "- access_level_instance_id: Only return records in this access level instance's subtree (defaults to the user's own)",
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
                    "cycle_id": "integer",
                    "results": ["object"],
                    "column_defs": [{"field": "string", "headerName": "string", "sortable": "boolean"}],
                },
                description="A page of records with their AG Grid column definitions. "
                "With ids_only, only `results` is returned, as a list of view IDs.",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def filter(self, request):
        """
        List all the properties or tax lots for angular ag grid
        """
        profile_id = request.data.get("profile_id", None)
        try:
            profile_id = int(profile_id)
        except (TypeError, ValueError):
            profile_id = None

        results = InventoryFilter(request, profile_id).get_filtered_results()
        return results

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("cycle_id", required=True, description="Cycle ID"),
            AutoSchemaHelper.query_enum_field("inventory_type", "properties or taxlots", ["properties", "taxlots"]),
        ],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "data": "integer", "message": "string"},
                description="The number of records in `data`, or an error `message` if the cycle is not found",
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def record_count(self, request):
        """
        Get the total number of records for the given cycle and inventory type in the user's access level instance
        """
        org_id = self.get_organization(request)
        inventory_type = self.request.query_params.get("inventory_type", None)
        cycle_id = self.request.query_params.get("cycle_id", None)

        if inventory_type not in ["properties", "taxlots"]:
            return JsonResponse({"status": "error", "message": "inventory_type must be 'properties' or 'taxlots'"}, status=400)

        try:
            cycle = Cycle.objects.get(id=cycle_id, organization_id=org_id)
        except Cycle.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        # count only the records in the user's access level instance's subtree
        ali = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        if inventory_type == "properties":
            views = cycle.propertyview_set.filter(
                property__access_level_instance__lft__gte=ali.lft, property__access_level_instance__rgt__lte=ali.rgt
            )
        else:
            views = cycle.taxlotview_set.filter(
                taxlot__access_level_instance__lft__gte=ali.lft, taxlot__access_level_instance__rgt__lte=ali.rgt
            )
        record_count = views.count()

        return JsonResponse({"status": "succes", "data": record_count}, status=200)
