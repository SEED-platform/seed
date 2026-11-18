"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import PropertyMeasure, PropertyView, Scenario
from seed.serializers.scenarios import ScenarioSerializer
from seed.utils.api import api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchNoCreateModelViewSet

property_view_id_path_field = AutoSchemaHelper.path_id_field("PropertyView ID", name="property_pk")


def get_property_view_state_ids(property_view_id):
    """IDs of the property view's current state and of the historical states in its history

    Scenarios and measures can belong to historical states, which are no longer linked to the property view.
    """
    property_view = PropertyView.objects.get(pk=property_view_id)
    history, _ = property_view.state.history()
    return {property_view.state_id, *(h["state_id"] for h in history)}


@extend_schema(parameters=[AutoSchemaHelper.query_org_id_field(), property_view_id_path_field])
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_viewer"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="list",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="update",
)
@method_decorator(
    [
        has_perm("requires_member"),
        has_hierarchy_access(property_view_id_kwarg="property_pk"),
    ],
    name="destroy",
)
class PropertyScenarioViewSet(SEEDOrgNoPatchNoCreateModelViewSet):
    """
    API View for Scenarios.
    """

    serializer_class = ScenarioSerializer
    parser_classes = (
        JSONParser,
        FormParser,
    )
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    orgfilter = "property_state__organization_id"

    enum_validators = {"temporal_status": Scenario.str_to_temporal_status}

    def get_queryset(self):
        # Authorization is partially implicit in that users can't try to query
        # on an org_id for an Organization that they are not a member of.
        org_id = self.get_organization(self.request)
        property_view_id = self.kwargs.get("property_pk")

        return Scenario.objects.filter(
            property_state__organization_id=org_id,
            property_state__propertyview=property_view_id,
        ).order_by("id")

    @extend_schema(
        request=AutoSchemaHelper.json_body(
            {
                "annual_cost_savings": "number",
                "annual_electricity_energy": "number",
                "annual_electricity_savings": "number",
                "annual_natural_gas_energy": "number",
                "annual_natural_gas_savings": "number",
                "annual_peak_demand": "number",
                "annual_peak_electricity_reduction": "number",
                "annual_site_energy": "number",
                "annual_site_energy_savings": "number",
                "annual_site_energy_use_intensity": "number",
                "annual_source_energy": "number",
                "annual_source_energy_savings": "number",
                "annual_source_energy_use_intensity": "number",
                "cdd": "number",
                "cdd_base_temperature": "number",
                "description": "string",
                "hdd": "number",
                "hdd_base_temperature": "number",
                "name": "string",
                "summer_peak_load_reduction": "number",
                "temporal_status": Scenario.TEMPORAL_STATUS_TYPES,
                "winter_peak_load_reduction": "number",
            },
            description="The scenario fields to update; any other key is rejected",
        ),
        responses={
            200: inline_serializer(
                "PropertyScenarioUpdateResponse", fields={"status": serializers.CharField(), "data": ScenarioSerializer()}
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    def update(self, request, property_pk=None, pk=None):
        """
        Where property_pk is the associated PropertyView.id
        """
        try:
            scenario = Scenario.objects.get(pk=pk, property_state_id__in=get_property_view_state_ids(property_pk))
        except Scenario.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No scenario found with given pks"}, status=status.HTTP_404_NOT_FOUND)

        # Only scalar fields can be set from the request; relations cannot be assigned raw values
        possible_fields = [f.name for f in scenario._meta.concrete_fields if not f.is_relation and not f.primary_key]

        for key, value in request.data.items():
            if key in possible_fields:
                # Handle enums
                updated_value = value
                if key in self.enum_validators:
                    updated_value = self.enum_validators[key](value)
                    if updated_value is None:
                        return JsonResponse({"Success": False, "Message": f"Invalid {key} value"}, status=status.HTTP_400_BAD_REQUEST)

                setattr(scenario, key, updated_value)
            else:
                return JsonResponse(
                    {"Success": False, "Message": f'"{key}" is not a valid scenario field'}, status=status.HTTP_400_BAD_REQUEST
                )

        try:
            scenario.save()
        except ValidationError as e:
            return JsonResponse({"Success": False, "Message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        result = {"status": "success", "data": ScenarioSerializer(scenario).data}

        return JsonResponse(result, status=status.HTTP_200_OK)

    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    def destroy(self, request, property_pk=None, pk=None):
        try:
            scenario = Scenario.objects.get(pk=pk, property_state_id__in=get_property_view_state_ids(property_pk))
        except Scenario.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No Scenario found with given pks"}, status=status.HTTP_404_NOT_FOUND)

        # A PropertyMeasure can be shared by several scenarios (e.g. a "package of all measures"
        # scenario references the same measures as the individual packages), so only delete the
        # ones that are orphaned once this scenario is gone.
        measure_ids = list(scenario.measures.values_list("id", flat=True))
        scenario.delete()
        PropertyMeasure.objects.filter(id__in=measure_ids, scenario__isnull=True).delete()

        # A 204 response must not have a body, otherwise the declared Content-Length does not
        # match what is sent and clients/proxies reject the response.
        return HttpResponse(status=status.HTTP_204_NO_CONTENT)
