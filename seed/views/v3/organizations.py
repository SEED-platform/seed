# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column

_log = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ViewSet):

    model = Column

    @ajax_request_class
    @has_perm_class('can_modify_data')
    @action(detail=True, methods=['DELETE'])
    def columns(self, request, pk=None):
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
        organization_id = pk
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
