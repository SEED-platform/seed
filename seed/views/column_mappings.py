# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

import coreapi
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import BaseFilterBackend
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.column_mappings import ColumnMapping
from seed.serializers.column_mappings import ColumnMappingSerializer
from seed.utils.api import OrgValidateMixin
from seed.utils.api import api_endpoint_class
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet

_log = logging.getLogger(__name__)


class ColumnMappingViewSetFilterBackend(BaseFilterBackend):
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


class ColumnMappingViewSet(OrgValidateMixin, SEEDOrgCreateUpdateModelViewSet):
    serializer_class = ColumnMappingSerializer
    renderer_classes = (JSONRenderer,)
    model = ColumnMapping
    pagination_class = None
    parser_classes = (JSONParser, FormParser)
    filter_backends = (ColumnMappingViewSetFilterBackend,)
    orgfilter = 'super_organization_id'
    # Do not return column mappings where the column_raw or the column_mapped fields are NULL.
    # This needs to be cleaned up in the near future to have the API clean up the column mappings
    # upon the deletion of a column.
    queryset = ColumnMapping.objects.exclude(
        Q(column_mapped__isnull=True) | Q(column_raw__isnull=True)
    )

    @ajax_request_class
    def retrieve(self, request, pk=None):
        queryset = ColumnMapping.objects.filter(
            super_organization_id=self.get_organization(request))
        try:
            data = get_object_or_404(queryset, pk=pk)
        except Http404:
            return JsonResponse({
                'status': 'error',
                'message': 'Could not find column mapping for organization'
            }, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse(ColumnMappingSerializer(data).data)

    @ajax_request_class
    @has_perm_class('can_modify_data')
    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.delete()
        except Http404:
            return JsonResponse({
                'status': 'success',
                'message': 'Column mapping with id and organization did not exist, nothing removed'
            }, )

        return JsonResponse({
            'status': 'success',
            'message': 'Column mapping deleted'
        }, status=status.HTTP_200_OK)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    @require_organization_id_class
    @action(detail=False, methods=['POST'])
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
        organization_id = self.get_organization(request)

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
