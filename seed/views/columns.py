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


class ColumnViewSetFilterBackend(BaseFilterBackend):
    """
    Specify the schema for the column view set. This allows the user to see the other
    required columns in Swagger.
    """

    def get_schema_fields(self, view):
        return [
            coreapi.Field('organization_id', location='query', required=True, type='integer'),
            coreapi.Field('inventory_type', location='query', required=False, type='string'),
            coreapi.Field('only_used', location='query', required=False, type='boolean'),
        ]

    def filter_queryset(self, request, queryset, view):
        return queryset


class ColumnViewSet(OrgValidateMixin, SEEDOrgCreateUpdateModelViewSet):
    raise_exception = True
    serializer_class = ColumnSerializer
    renderer_classes = (JSONRenderer,)
    model = Column
    pagination_class = NoPagination
    parser_classes = (JSONParser, FormParser)
    # pagination_class = NoPagination
    filter_backends = (ColumnViewSetFilterBackend,)

    def get_queryset(self):
        # check if the request is properties or taxlots
        org_id = self.get_organization(self.request)
        return Column.objects.filter(organization_id=org_id)

    @ajax_request_class
    def list(self, request):
        """
        Retrieves all columns for the user's organization including the raw database columns. Will
        return all the columns across both the Property and Tax Lot tables. The related field will
        be true if the column came from the other table that is not the "inventory_type" (which
        defaults to Property)

            This is the same results as calling /api/v2/<inventory_type>/columns/?organization_id={}

            Example: /api/v2/columns/?inventory_type=(property|taxlot)\&organization_id={}

            type:
                status:
                    required: true
                    type: string
                    description: Either success or error
                columns:
                    required: true
                    type: array[column]
                    description: Returns an array where each item is a full column structure.
            parameters:
                - name: organization_id
                  description: The organization_id for this user's organization
                  required: true
                  paramType: query
                - name: inventory_type
                  description: Which inventory type is being matched (for related fields and naming).
                    property or taxlot
                  required: true
                  paramType: query
                - name: used_only
                  description: Determine whether or not to show only the used fields (i.e. only columns that have been mapped)
                  type: boolean
                  required: false
                  paramType: query
        """
        organization_id = self.get_organization(self.request)
        inventory_type = request.query_params.get('inventory_type', 'property')
        only_used = request.query_params.get('only_used', False)
        columns = Column.retrieve_all(organization_id, inventory_type, only_used)
        return JsonResponse({
            'status': 'success',
            'columns': columns,
        })

    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Retrieves a column (Column)

            type:
                status:
                    required: true
                    type: string
                    description: Either success or error
                column:
                    required: true
                    type: dictionary
                    description: Returns a dictionary of a full column structure with keys such as
                                 keys ''name'', ''id'', ''is_extra_data'', ''column_name'',
                                 ''table_name'',...
            parameters:
                - name: organization_id
                  description: The organization_id for this user's organization
                  required: true
                  paramType: query
        """
        organization_id = self.get_organization(self.request)

        # check if column exists for the organization
        try:
            c = Column.objects.get(pk=pk)
        except Column.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'column with id {} does not exist'.format(pk)
            }, status=status.HTTP_404_NOT_FOUND)

        if c.organization.id != organization_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Organization ID mismatch between column and organization'
            }, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({
            'status': 'success',
            'column': ColumnSerializer(c).data
        })

    @ajax_request_class
    @has_perm_class('can_modify_data')
    @list_route(methods=['POST'])
    def delete_all(self, request):
        """
        Delete all columns for an organization. This method is typically not recommended if there
        are data in the inventory as it will invalidate all extra_data fields. This also removes
        all the column mappings that existed.

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
            column_mappings_deleted_count:
                description: Number of column_mappings that were deleted
                type: integer
                required: true
            columns_deleted_count:
                description: Number of columns that were deleted
                type: integer
                required: true
        """
        organization_id = request.query_params.get('organization_id', None)

        try:
            org = Organization.objects.get(pk=organization_id)
            c_count, cm_count = Column.delete_all(org)
            return JsonResponse(
                {
                    'status': 'success',
                    'column_mappings_deleted_count': cm_count,
                    'columns_deleted_count': c_count,
                }
            )
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization with with id {} does not exist'.format(organization_id)
            }, status=status.HTTP_404_NOT_FOUND)

    @list_route(renderer_classes=(SEEDJSONRenderer,))
    def add_column_names(self, request):
        """
        Allow columns to be added based on an existing record.
        This may be necessary to make column selections available when
        records are upload through API endpoint rather than the frontend.
        """
        model_obj = None
        org = self.get_organization(request, return_obj=True)
        inventory_pk = request.query_params.get('inventory_pk')
        inventory_type = request.query_params.get('inventory_type', 'property')
        if inventory_type in ['property', 'propertystate']:
            if not inventory_pk:
                model_obj = PropertyState.objects.filter(
                    organization=org
                ).order_by('-id').first()
            try:
                model_obj = PropertyState.objects.get(id=inventory_pk)
            except PropertyState.DoesNotExist:
                pass
        elif inventory_type in ['taxlot', 'taxlotstate']:
            if not inventory_pk:
                model_obj = TaxLotState.objects.filter(
                    organization=org
                ).order_by('-id').first()
            else:
                try:
                    model_obj = TaxLotState.objects.get(id=inventory_pk)
                    inventory_type = 'taxlotstate'
                except TaxLotState.DoesNotExist:
                    pass
        else:
            msg = "{} is not a valid inventory type".format(inventory_type)
            raise ParseError(msg)
        if not model_obj:
            msg = "No {} was found matching {}".format(
                inventory_type, inventory_pk
            )
            raise NotFound(msg)
        Column.save_column_names(model_obj)

        columns = Column.objects.filter(
            organization=model_obj.organization,
            table_name=model_obj.__class__.__name__,
            is_extra_data=True,

        )
        columns = ColumnSerializer(columns, many=True)
        return Response(columns.data, status=status.HTTP_200_OK)


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
