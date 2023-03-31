# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from copy import deepcopy

import django.core.exceptions
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models.columns import Column
from seed.models.data_views import DataView
from seed.serializers.data_views import DataViewSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)


class DataViewViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = DataViewSerializer
    model = DataView

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        organization_id = self.get_organization(request)
        data_view_queryset = DataView.objects.filter(organization=organization_id)

        return JsonResponse({
            'status': 'success',
            'data_views': DataViewSerializer(data_view_queryset, many=True).data
        }, status=status.HTTP_200_OK)

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
                'data_view': DataViewSerializer(
                    DataView.objects.get(id=pk, organization=organization)
                ).data
            }, status=status.HTTP_200_OK)
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            DataView.objects.get(id=pk, organization=organization_id).delete()
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted DataView ID {pk}'
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'columns': ['integer'],
                'cycles': ['integer'],
                'data_aggregations': ['integer'],
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def create(self, request):
        org_id = self.get_organization(request)
        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = DataViewSerializer(data=data)

        if not serializer.is_valid():
            error_response = {
                'status': 'error',
                'message': 'Data Validation Error',
                'errors': serializer.errors
            }

            return JsonResponse(error_response, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'data_view': serializer.data
            }, status=status.HTTP_200_OK)
        except django.core.exceptions.ValidationError as e:

            message_dict = e.message_dict
            return JsonResponse({
                'status': 'error',
                'message': 'Bad Request',
                'errors': message_dict
            }, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'columns': ['integer'],
                'cycles': ['integer'],
                'data_aggregations': ['integer'],
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def update(self, request, pk):
        org_id = self.get_organization(request)

        data_view = None
        try:
            data_view = DataView.objects.get(id=pk, organization=org_id)
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = DataViewSerializer(data_view, data=data, partial=True)
        if not serializer.is_valid():
            return JsonResponse({
                'status': 'error',
                'message': 'Bad Request',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            serializer.save()
            return JsonResponse({
                'status': 'success',
                'data_view': serializer.data,
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

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'columns': ['integer'],
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['PUT'])
    def evaluate(self, request, pk):
        organization = self.get_organization(request)
        deepcopy(request.data)
        data = deepcopy(request.data)

        try:
            data_view = DataView.objects.get(id=pk, organization=organization)
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        columns = Column.objects.filter(id__in=data['columns'])
        if len(columns) != len(data['columns']):
            return JsonResponse({
                'status': 'error',
                'message': f'Columns with ids {data["columns"]} do not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        response = data_view.evaluate(columns)
        return JsonResponse({
            'status': 'success',
            'data': response
        })

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def inventory(self, request, pk):
        organization = self.get_organization(request)
        deepcopy(request.data)

        try:
            data_view = DataView.objects.get(id=pk, organization=organization)
        except DataView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'DataView with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        response = data_view.get_inventory()
        return JsonResponse({
            'status': 'success',
            'data': response
        })
