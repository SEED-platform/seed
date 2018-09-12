# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

import coreapi
from django.http import JsonResponse
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import list_route, detail_route
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.filters import BaseFilterBackend
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import PropertyState, TaxLotState
from seed.models.columns import Column, ColumnMapping
from seed.pagination import NoPagination
from seed.renderers import SEEDJSONRenderer
from seed.serializers.columns import ColumnSerializer
from seed.utils.api import OrgValidateMixin
from seed.utils.api import api_endpoint_class
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet

_log = logging.getLogger(__name__)


class ColumnMappingiewSetFilterBackend(BaseFilterBackend):
    """
    Specify the schema for the column view set. This allows the user to see the other
    required columns in Swagger.
    """

    def get_schema_fields(self, view):
        return [
            coreapi.Field('organization_id', location='query', required=True, type='integer'),
        ]

    def filter_queryset(self, request, queryset, view):
        return queryset


class ColumnMappingViewSet(viewsets.ViewSet):
    raise_exception = True

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all column mappings for the user's organization.
        ---
        type:
            status:
                required: true
                type: string
                description: Either success or error
            column_mappings:
                required: true
                type: array[column]
                description: Returns an array where each item is a full column_mapping structure,
                             including keys ''name'', ''id'', ''raw column'', ''mapped column''

        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        organization_id = request.query_params.get('organization_id', None)
        org = Organization.objects.get(pk=organization_id)
        column_mappings = []
        for cm in ColumnMapping.objects.filter(super_organization=org):
            # find the raw and mapped column
            column_mappings.append(cm.to_dict())

        return JsonResponse({
            'status': 'success',
            'column_mappings': column_mappings,
        })

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
            Retrieves a column_mapping (ColumnMapping)
            ---
            type:
                status:
                    required: true
                    type: string
                    description: Either success or error
                column:
                    required: true
                    type: dictionary
                    description: Returns a dictionary of a column_mapping structure,
                                 keys ''name'', ''id'', ''is_extra_data'', ''column_name'',
                                 ''table_name'',...
            parameters:
                - name: organization_id
                  description: The organization_id for this user's organization
                  required: true
                  paramType: query
        """
        organization_id = request.query_params.get('organization_id', None)
        valid_orgs = OrganizationUser.objects.filter(
            user_id=request.user.id
        ).values_list('organization_id', flat=True).order_by('organization_id')
        if organization_id not in valid_orgs:
            return JsonResponse({
                'status': 'error',
                'message': 'Cannot access column_mappings for this organization id',
            }, status=status.HTTP_403_FORBIDDEN)

        # check if column exists for the organization
        try:
            cm = ColumnMapping.objects.get(pk=pk)
        except ColumnMapping.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'column_mapping with id {} does not exist'.format(pk)
            }, status=status.HTTP_404_NOT_FOUND)

        if cm.super_organization.id != organization_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Organization ID mismatch between column_mappings and organization'
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({
            'status': 'success',
            'column_mapping': cm.to_dict(),
        })

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @detail_route(methods=['DELETE'])
    def delete(self, request, pk=None):
        """
        Delete a column mapping
        ---
        parameters:
            - name: pk
              description: Primary key to delete
              require: true
        """
        organization_id = request.query_params.get('organization_id')

        try:
            org = Organization.objects.get(pk=organization_id)
            delete_count, _ = ColumnMapping.objects.filter(
                super_organization=org, pk=int(pk)
            ).delete()
            if delete_count > 0:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Column mapping deleted'
                })
            else:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Column mapping with id and organization did not exist, nothing removed'
                })
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with id %s does not exist' % organization_id
            }, status=status.HTTP_404_NOT_FOUND)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @require_organization_id_class
    @list_route(methods=['POST'])
    def delete_all(self, request):
        """
        Delete all column mappings for an organization
        ---
        parameters:
            - name: organization_id
              description: The organization_id
              required: true
              paramType: query
        type:
            status:
                description: success or error
                type: string
                required: true
            delete_count:
                description: Number of column_mappings that were deleted
                type: integer
                required: true
        """
        organization_id = request.query_params.get('organization_id')

        try:
            org = Organization.objects.get(pk=organization_id)
            delete_count = ColumnMapping.delete_mappings(org)
            return JsonResponse(
                {
                    'status': 'success',
                    'delete_count': delete_count,
                }
            )
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with id %s does not exist' % organization_id
            }, status=status.HTTP_404_NOT_FOUND)
