# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.http import JsonResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request_class
from seed.models import Scenario
from seed.serializers.scenarios import ScenarioSerializer
from seed.utils.api import api_endpoint_class
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
