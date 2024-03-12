# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import (
    has_hierarchy_access,
    has_perm_class
)
from seed.models import PropertyMeasure, PropertyView
from seed.serializers.scenarios import PropertyMeasureSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchNoCreateModelViewSet


class PropertyMeasureViewSet(SEEDOrgNoPatchNoCreateModelViewSet):
    """
    API view for PropertyMeasures
    """
    serializer_class = PropertyMeasureSerializer
    model = PropertyMeasure
    pagination_class = None
    orgfilter = 'property_state__organization_id'

    enum_validators = {
        'application_scale': PropertyMeasure.str_to_application_scale,
        'category_affected': PropertyMeasure.str_to_category_affected,
        'implementation_status': PropertyMeasure.str_to_impl_status
    }

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
    def list(self, request, property_pk=None, scenario_pk=None):
        """
        Where property_pk is the associated PropertyView.id
        """
        try:
            property_state = PropertyView.objects.get(pk=property_pk).state
        except PropertyView.DoesNotExist:
            return JsonResponse({
                "status": 'error',
                "message": 'No PropertyView found for given pks'
            }, status=status.HTTP_404_NOT_FOUND)

        measure_set = PropertyMeasure.objects.filter(scenario=scenario_pk, property_state=property_state.id)

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
    @has_perm_class('can_view_data')
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
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

    @swagger_auto_schema(
        request_body=AutoSchemaHelper.schema_factory(
            {
                "application_scale": PropertyMeasure.APPLICATION_SCALE_TYPES,
                "category_affected": PropertyMeasure.CATEGORY_AFFECTED_TYPE,
                "cost_capital_replacement": "integer",
                "cost_installation": "integer",
                "cost_material": "integer",
                "cost_mv": "integer",
                "cost_residual_value": "integer",
                "cost_total_first": "integer",
                "description": "string",
                "implementation_status": PropertyMeasure.IMPLEMENTATION_TYPES,
                "property_measure_name": "string",
                "recommended": "boolean",
                "useful_life": "integer",
            }
        )
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
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
                # Handle enums
                if key in self.enum_validators.keys():
                    value = self.enum_validators[key](value)
                    if value is None:
                        return JsonResponse({
                            "Success": False,
                            "Message": f"Invalid {key} value"
                        }, status=status.HTTP_400_BAD_REQUEST)

                setattr(property_measure, key, value)
            else:
                return JsonResponse({
                    "status": 'error',
                    "message": f'"{key}" is not a valid property measure field'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            property_measure.save()
        except ValidationError as e:
            return JsonResponse({
                "Success": False,
                "Message": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        result = {
            "status": "success",
            "data": PropertyMeasureSerializer(property_measure).data
        }

        return JsonResponse(result, status=status.HTTP_200_OK)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_view_data')
    @has_hierarchy_access(property_view_id_kwarg="property_pk")
    def destroy(self, request, property_pk=None, scenario_pk=None, pk=None):
        try:
            # property_state = PropertyView.objects.get(pk=property_pk).state
            # Can't use property_view to find measures on historical property_states.
            # When New scenarios and measures are created the previous property_state looses its connection
            # to a property_view.
            property_measure = PropertyMeasure.objects.get(pk=pk, scenario=scenario_pk)
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
