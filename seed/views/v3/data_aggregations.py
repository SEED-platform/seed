# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from copy import deepcopy

import django.core.exceptions
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models.data_aggregations import DataAggregation
from seed.serializers.data_aggregations import DataAggregationSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)


class DataAggregationViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DataAggregationSerializer
    model = DataAggregation

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        organization_id = self.get_organization(request)
        data_aggregation_queryset = DataAggregation.objects.filter(organization=organization_id)

        return JsonResponse({
            'status': 'success',
            'message': DataAggregationSerializer(data_aggregation_queryset, many=True).data
        })

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            DataAggregation.objects.get(id=pk, organization=organization_id).delete()
        except DataAggregation.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataAggregation with id {pk} does not exist'
            })

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted DataAggreation ID {pk}'
        })

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'column': 'integer',
                'type': 'string',
                'name': 'string',
            },
            description='-type: "Average", "Count", "Max", "Min", or "Sum'
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def create(self, request):
        org_id = self.get_organization(request)
        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = DataAggregationSerializer(data=data)

        if not serializer.is_valid():
            error_response = {
                'status': 'Error',
                'message': 'Data Validation Error',
                'errors': serializer.errors
            }
            if serializer.errors.get("type"):
                error_response['suggestion'] = "Valid Types are 'Average', 'Count', 'Max', 'Min', 'Sum'"

            return JsonResponse(error_response)

        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'data_aggregation': serializer.data
            })
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict
            return JsonResponse({
                'status': 'error',
                'message': 'Bad Request',
                'errors': message_dict
            })

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk):
        organization = self.get_organization(request)

        try:
            return JsonResponse({
                'status': 'success',
                'data_aggregation': DataAggregationSerializer(
                    DataAggregation.objects.get(id=pk, organization=organization)
                ).data
            })
        except DataAggregation.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataAggregation with id {pk} does not exist'
            })

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'column': 'integer',
                'type': 'string',
                'name': 'string',
            },
            description='-type: "Average", "Count", "Max", "Min", or "Sum'
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def update(self, request, pk):
        organization = self.get_organization(request)

        data_aggregation = None
        try:
            data_aggregation = DataAggregation.objects.get(id=pk, organization=organization)
        except DataAggregation.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataAggregation with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        data.update({'organization': organization})
        serializer = DataAggregationSerializer(data_aggregation, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'data_aggregation': serializer.data,
            }, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:
            message_dict = e.message_dict

            # rename key __all__ to general to make it more user friendly
            if '__all__' in message_dict:
                message_dict['general'] = message_dict.pop('__all__')

            return JsonResponse({
                'status': 'error',
                'message': 'Bad request',
                'errors': message_dict,
            }, status=status.HTTP_400_BAD_REQUEST)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['GET'])
    def evaluate(self, request, pk):
        organization = self.get_organization(request)
        deepcopy(request.data)

        try:
            data_aggregation = DataAggregation.objects.get(id=pk, organization=organization)
        except DataAggregation.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataAggregation with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        value = data_aggregation.evaluate()
        return JsonResponse({
            'status': 'success',
            'data': value
        })
