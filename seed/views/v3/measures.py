# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.models import (
    Measure,
)
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param


@method_decorator(
    name='retrieve',
    decorator=swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_integer_field(
            name="id",
            required=True,
            description="A unique integer value identifying this measure.")]
    ),
)
class MeasureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    list:
        Return a list of all measures

    retrieve:
        Return a measure by a unique id

    """
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    queryset = Measure.objects.all()
    pagination_class = None

    @swagger_auto_schema_org_query_param
    @action(detail=False, methods=['POST'])
    def reset(self, request):
        """
        Reset all the measures back to the defaults (as provided by BuildingSync)
        ---
        parameters: {}
        type:
            organization_id:
                required: true
                type: integer
                paramType: query
            status:
                required: true
                type: string
                description: Either success or error
            measures:
                required: true
                type: list
                description: list of measures
        """
        organization_id = request.query_params.get('organization_id', None)
        if not organization_id:
            return JsonResponse({
                'status': 'error', 'message': 'organization_id not provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        Measure.populate_measures(organization_id)
        data = dict(measures=list(
            Measure.objects.filter(organization_id=organization_id).order_by('id').values())
        )

        data['status'] = 'success'
        return JsonResponse(data)
