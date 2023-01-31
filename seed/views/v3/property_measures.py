# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.utils.decorators import method_decorator
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer
from seed.decorators import ajax_request_class
from seed.utils.api import api_endpoint_class
from seed.models import PropertyMeasure
from seed.serializers.scenarios import PropertyMeasureSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from django.http import JsonResponse
from rest_framework import status
from seed.utils.viewsets import SEEDOrgModelViewSet



@method_decorator(name='list', decorator=swagger_auto_schema_org_query_param)
@method_decorator(name='retrieve', decorator=swagger_auto_schema_org_query_param)
@method_decorator(name='destroy', decorator=swagger_auto_schema_org_query_param)
class PropertyMeasureViewSet(SEEDOrgModelViewSet):
    """
    API view for PropertyMeasures
    """
    serializer_class = PropertyMeasureSerializer   
    model = PropertyMeasure 
    parser_classes = (JSONParser, FormParser,)
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    orgfilter = 'property_state__organization_id'

    @api_endpoint_class
    @ajax_request_class
    def list(self, request, property_pk=None, scenario_pk=None):

        measure_set = PropertyMeasure.objects.filter(scenario=scenario_pk)
        if not measure_set:
            return JsonResponse({                  
                "status": 'error',
                "message": f'No Measures found for given scenario_pk'
            }, status=status.HTTP_404_NOT_FOUND)

        serialized_measures = []
        for measure in measure_set:
            serialized_measure = PropertyMeasureSerializer(measure).data
            serialized_measures.append(serialized_measure)
        
        return JsonResponse({
            'status': 'success',
            'data': serialized_measures
        }, status=status.HTTP_200_OK)

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, property_pk=None, scenario_pk=None, pk=None):

        try: 
            measure = PropertyMeasure.objects.get(pk=pk, scenario=scenario_pk)
        except PropertyMeasure.DoesNotExist:
            return JsonResponse({                  
                "status": 'error',
                "message": 'No Measure found for given pk and scenario_pk'
            }, status=status.HTTP_404_NOT_FOUND)

        serialized_measure = PropertyMeasureSerializer(measure).data 

        return JsonResponse({
            "status": 'success',
            "data": serialized_measure
        }, status=status.HTTP_200_OK)



    # @swagger_auto_schema(
    #     manual_parameters=[
    #         AutoSchemaHelper.query_org_id_field(),
    #         AutoSchemaHelper.query_integer_field(
    #             name='property_pk',
    #             required=True,
    #             description='Associated PropertyView ID (not PropertyState).',
    #         ),
    #         AutoSchemaHelper.query_integer_field(
    #             name="id",
    #             required=True,
    #             description="Scenario ID"
    #         )
    #     ],
    # )
    # @api_endpoint_class
    # @ajax_request_class
    # def update(self, request, property_pk=None, pk=None):
    #     property_measure = PropertyMeasure.objects.get(pk=pk)
    #     breakpoint()
