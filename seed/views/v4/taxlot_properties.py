from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import OrgMixin, ProfileIdMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.v4.inventory_filter import get_filtered_results


class TaxLotPropertyViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin, ProfileIdMixin):
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("inventory_type", required=False, description="property or taxlot"),
            AutoSchemaHelper.query_integer_field("cycle", required=False, description="The ID of the cycle to get properties"),
            AutoSchemaHelper.query_integer_field("per_page", required=False, description="Number of properties per page"),
            AutoSchemaHelper.query_integer_field("page", required=False, description="Page to fetch"),
            AutoSchemaHelper.query_boolean_field(
                "include_related",
                required=False,
                description="If False, related data (i.e., Tax Lot data) is not added to the response (default is True)",
            ),
            AutoSchemaHelper.query_boolean_field(
                "ids_only", required=False, description="Function will return a list of property ids instead of property objects"
            ),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                "profile_id": "integer",
                "property_view_ids": ["integer"],
            },
            description="Properties:\n"
            "- profile_id: Either an id of a list settings profile, or undefined\n"
            "- property_view_ids: List of property view ids",
        ),
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["POST"])
    def filter(self, request):
        """
        List all the properties for angular ag grid
        """
        profile_id = request.data.get("profile_id", None)
        try:
            profile_id = int(profile_id)
        except (TypeError, ValueError):
            profile_id = None

        results = get_filtered_results(request, profile_id)
        return JsonResponse(results)
