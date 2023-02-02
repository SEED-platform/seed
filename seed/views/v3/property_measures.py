# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.http import JsonResponse
from rest_framework import status

from seed.decorators import ajax_request_class
from seed.models import PropertyMeasure, PropertyView
from seed.serializers.scenarios import PropertyMeasureSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.viewsets import SEEDOrgNoPatchNoCreateModelViewSet


class PropertyMeasureViewSet(SEEDOrgNoPatchNoCreateModelViewSet):
    """
    API view for PropertyMeasures
    """
    serializer_class = PropertyMeasureSerializer
    model = PropertyMeasure
    orgfilter = 'property_state__organization_id'

    @api_endpoint_class
    @ajax_request_class
    def list(self, request, property_pk=None, scenario_pk=None):
        """
        Where property_pk is the associated PropertyView.id
        """
        try:
            property_state = PropertyView.objects.get(pk=property_pk).state
        except PropertyView.DoesNotExist:
            return JsonResponse({
                "status": 'error',
                "message": 'No Measures found for given pks'
            }, status=status.HTTP_404_NOT_FOUND)

        measure_set = PropertyMeasure.objects.filter(scenario=scenario_pk, property_state=property_state.id)
        if not measure_set:
            return JsonResponse({
                "status": 'error',
                "message": 'No Measures found for given pks'
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
        """
        Where property_pk is the associated PropertyView.id
        """

        try:
            property_state = PropertyView.objects.get(pk=property_pk).state
            measure = PropertyMeasure.objects.get(pk=pk, scenario=scenario_pk, property_state=property_state.id)
        except (PropertyMeasure.DoesNotExist, PropertyView.DoesNotExist):
            return JsonResponse({
                "status": 'error',
                "message": 'No Measure found for given pks'
            }, status=status.HTTP_404_NOT_FOUND)

        serialized_measure = PropertyMeasureSerializer(measure).data

        return JsonResponse({
            "status": 'success',
            "data": serialized_measure
        }, status=status.HTTP_200_OK)

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, property_pk=None, scenario_pk=None, pk=None):
        """
        Where property_pk is the associated PropertyView.id
        """
        try:
            property_state = PropertyView.objects.get(pk=property_pk).state
            property_measure = PropertyMeasure.objects.get(pk=pk, scenario=scenario_pk, property_state=property_state.id)
        except (PropertyMeasure.DoesNotExist, PropertyView.DoesNotExist):
            return JsonResponse({
                "status": "error",
                "message": 'No Property Measure found with given pks'
            }, status=status.HTTP_404_NOT_FOUND)

        possible_fields = [f.name for f in property_measure._meta.get_fields()]

        for key, value in request.data.items():
            if key in possible_fields:
                setattr(property_measure, key, value)
            else:
                return JsonResponse({
                    "status": 'error',
                    "message": f'"{key}" is not a valid property measure field'
                }, status=status.HTTP_400_BAD_REQUEST)

        property_measure.save()

        result = {
            "status": "success",
            "data": PropertyMeasureSerializer(property_measure).data
        }

        return JsonResponse(result, status=status.HTTP_200_OK)

    @api_endpoint_class
    @ajax_request_class
    def destroy(self, request, property_pk=None, scenario_pk=None, pk=None):
        try:
            property_state = PropertyView.objects.get(pk=property_pk).state
            property_measure = PropertyMeasure.objects.get(pk=pk, scenario=scenario_pk, property_state=property_state.id)
        except (PropertyMeasure.DoesNotExist, PropertyView.DoesNotExist):
            return JsonResponse({
                "status": "error",
                "message": 'No Property Measure found with given pks'
            }, status=status.HTTP_404_NOT_FOUND)

        property_measure.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'Successfully Deleted Property Measure'
        }, status=status.HTTP_200_OK)
