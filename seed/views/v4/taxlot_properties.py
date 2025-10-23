from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import Cycle
from seed.serializers.tax_lot_properties import TaxLotPropertySerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.v4.inventory_filter import InventoryFilter


class TaxLotPropertyViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin):
    serializer_class = TaxLotPropertySerializer

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
        List all the properties for angular ag grid
        """
        profile_id = request.data.get("profile_id", None)
        try:
            profile_id = int(profile_id)
        except (TypeError, ValueError):
            profile_id = None

        results = InventoryFilter(request, profile_id).get_filtered_results()
        return results

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("cycle_id", required=True, description="Cycle ID"),
            AutoSchemaHelper.query_string_field("inventory_type", required=True, description="properties or taxlots"),
        ]
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
        Get the total number of records for the given cycle and inventory type
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

        if inventory_type == "properties":
            record_count = cycle.propertyview_set.count()
        else:
            record_count = cycle.taxlotview_set.count()

        return JsonResponse({"status": "succes", "data": record_count}, status=200)
