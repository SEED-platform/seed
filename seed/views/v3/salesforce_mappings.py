# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from copy import deepcopy

import django.core.exceptions
from django.db import IntegrityError
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.salesforce_mappings import SalesforceMapping
from seed.serializers.salesforce_mappings import SalesforceMappingSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import (
    AutoSchemaHelper,
    swagger_auto_schema_org_query_param
)


class SalesforceMappingViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = SalesforceMappingSerializer
    model = SalesforceMapping

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        organization_id = self.get_organization(request)
        salesforce_mappings = SalesforceMapping.objects.filter(organization=organization_id)

        return JsonResponse({
            'status': 'success',
            'salesforce_mappings': SalesforceMappingSerializer(salesforce_mappings, many=True).data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk=0):
        organization = self.get_organization(request)
        if pk == 0:
            try:
                return JsonResponse({
                    'status': 'success',
                    'salesforce_mapping': SalesforceMappingSerializer(
                        SalesforceMapping.objects.filter(organization=organization).first()
                    ).data
                }, status=status.HTTP_200_OK)
            except Exception:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No mappings exist with this identifier'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                return JsonResponse({
                    'status': 'success',
                    'salesforce_mapping': SalesforceMappingSerializer(
                        SalesforceMapping.objects.get(id=pk, organization=organization)
                    ).data
                }, status=status.HTTP_200_OK)
            except SalesforceMapping.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': f'SalesforceMapping with id {pk} does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema_org_query_param
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def destroy(self, request, pk):
        organization_id = self.get_organization(request)

        try:
            SalesforceMapping.objects.get(id=pk, organization=organization_id).delete()
        except SalesforceMapping.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'SalesforceMapping with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse({
            'status': 'success',
            'message': f'Successfully deleted SalesforceMapping ID {pk}'
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'column': 'integer',
                'salesforce_fieldname': 'string',
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def create(self, request):

        org_id = int(self.get_organization(request))
        try:
            Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'bad organization_id'},
                                status=status.HTTP_400_BAD_REQUEST)

        data = deepcopy(request.data)
        data.update({'organization_id': org_id})
        serializer = SalesforceMappingSerializer(data=data)

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
                'salesforce_mapping': serializer.data
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
                'column': 'integer',
                'salesforce_fieldname': 'string',
            },
        )
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def update(self, request, pk):
        org_id = self.get_organization(request)
        try:
            salesforce_mapping = SalesforceMapping.objects.get(id=pk, organization=org_id)
        except SalesforceMapping.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'SalesforceMapping with id {pk} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        data = deepcopy(request.data)
        data.update({'organization': org_id})
        serializer = SalesforceMappingSerializer(salesforce_mapping, data=data, partial=True)
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
                'salesforce_mapping': serializer.data,
            }, status=status.HTTP_200_OK)
        except IntegrityError:
            return JsonResponse({
                'status': 'error',
                'message': 'Duplicate records are not allowed',
            }, status=status.HTTP_400_BAD_REQUEST)
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
        manual_parameters=[AutoSchemaHelper.query_org_id_field()]
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @action(detail=True, methods=['GET'])
    def evaluate(self, request, pk):
        organization = self.get_organization(request)
        deepcopy(request.data)

        try:
            salesforce_mapping = SalesforceMapping.objects.get(id=pk, organization=organization)
        except Exception:
            return JsonResponse({
                'status': 'error',
                'message': 'SalesforceMapping does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        response = salesforce_mapping.evaluate()

        return JsonResponse({
            'status': 'success',
            'data': response
        })
