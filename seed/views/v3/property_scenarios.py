# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request_class
from seed.models import Scenario
from seed.serializers.scenarios import ScenarioSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchNoCreateModelViewSet


class PropertyScenarioViewSet(SEEDOrgNoPatchNoCreateModelViewSet):
    """
    API View for Scenarios.
    """
    serializer_class = ScenarioSerializer
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    orgfilter = 'property_state__organization_id'

    def get_queryset(self):
        # Authorization is partially implicit in that users can't try to query
        # on an org_id for an Organization that they are not a member of.
        org_id = self.get_organization(self.request)
        property_view_id = self.kwargs.get('property_pk')

        return Scenario.objects.filter(
            property_state__organization_id=org_id,
            property_state__propertyview=property_view_id,
        ).order_by('id')

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                "measures": [
                    {
                        "application_scale": "integer",
                        "category_affected": "integer",
                        "cost_capital_replacement": "integer",
                        "cost_installation": "integer",
                        "cost_material": "integer",
                        "cost_mv": "integer",
                        "cost_residual_value": "integer",
                        "cost_total_first": "integer",
                        "description": "string",
                        "implementation_status": "integer",
                        "property_measure_name": "string",
                        "recommended": "string",
                        "useful_life": "integer",
                    }
                ],
                "annual_cost_savings": "integer",
                "annual_electricity_energy": "integer",
                "annual_electricity_savings": "integer",
                "annual_natural_gas_energy": "integer",
                "annual_natural_gas_savings": "integer",
                "annual_peak_demand": "integer",
                "annual_peak_electricity_reduction": "integer",
                "annual_site_energy": "integer",
                "annual_site_energy_savings": "integer",
                "annual_site_energy_use_intensity": "integer",
                "annual_source_energy": "integer",
                "annual_source_energy_savings": "integer",
                "annual_source_energy_use_intensity": "integer",
                "cdd": "integer",
                "cdd_base_temperature": "integer",
                "description": "string",
                "hdd": "integer",
                "hdd_base_temperature": "integer",
                "name": "string",
                "property_state": "integer",
                "reference_case": "integer",
                "summer_peak_load_reduction": "integer",
                "temporal_status": "integer",
                "winter_peak_load_reduction": "integer",
            }
        )
    )
    @api_endpoint_class
    @ajax_request_class
    def update(self, request, property_pk=None, pk=None):
        """
        Where property_pk is the associated PropertyView.id
        """
        scenario = Scenario.objects.get(pk=pk)
        possible_fields = [f.name for f in scenario._meta.get_fields()]

        for key, value in request.data.items():
            if key in possible_fields:
                setattr(scenario, key, value)
            else:
                return JsonResponse({
                    "Success": False,
                    "Message": f'"{key}" is not a valid scenario field'
                }, status=status.HTTP_400_BAD_REQUEST)

        scenario.save()

        result = {
            "status": "success",
            "data": ScenarioSerializer(scenario).data
        }

        return JsonResponse(result, status=status.HTTP_200_OK)

    @api_endpoint_class
    @ajax_request_class
    def destroy(self, request, property_pk=None, pk=None):
        try:
            scenario = Scenario.objects.get(pk=pk)
            measures = scenario.measures.all()
        except Scenario.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": 'No Scenario found with given pks'
            }, status=status.HTTP_404_NOT_FOUND)

        for property_measure in measures:
            property_measure.delete()
        scenario.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'Successfully Deleted Scenario'
        }, status=status.HTTP_204_NO_CONTENT)
