# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

from django.http import JsonResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column
from seed.models import ImportFile
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper

_log = logging.getLogger(__name__)


class MappingSerializer(serializers.Serializer):
    from_field = serializers.CharField()
    from_units = serializers.CharField()
    to_field = serializers.CharField()
    to_field_display_name = serializers.CharField()
    to_table_name = serializers.CharField()


class SaveColumnMappingsRequestPayloadSerializer(serializers.Serializer):
    """
    Example:
    {
        "mappings": [
            {
                'from_field': 'eui',  # raw field in import file
                'from_units': 'kBtu/ft**2/year', # pint-parsable units, optional
                'to_field': 'energy_use_intensity',
                'to_field_display_name': 'Energy Use Intensity',
                'to_table_name': 'PropertyState',
            },
            {
                'from_field': 'gfa',
                'from_units': 'ft**2', # pint-parsable units, optional
                'to_field': 'gross_floor_area',
                'to_field_display_name': 'Gross Floor Area',
                'to_table_name': 'PropertyState',
            }
        ]
    }
    """
    mappings = serializers.ListField(child=MappingSerializer())


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
            - name: pk
              description: The organization_id
              required: true
              paramType: path
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
        try:
            org = Organization.objects.get(pk=pk)
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
                'message': 'organization with with id {} does not exist'.format(pk)
            }, status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_integer_field(
                'import_file_id', required=True, description='Import file id'),
            openapi.Parameter(
                'id', openapi.IN_PATH, type=openapi.TYPE_INTEGER, description='Organization id'),
        ],
        request_body=SaveColumnMappingsRequestPayloadSerializer,
        responses={
            200: 'success response'
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['POST'])
    def column_mappings(self, request, pk=None):
        """
        Saves the mappings between the raw headers of an ImportFile and the
        destination fields in the `to_table_name` model which should be either
        PropertyState or TaxLotState

        Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``
        """
        import_file_id = request.query_params.get('import_file_id')
        if import_file_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'Query param `import_file_id` is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            _ = ImportFile.objects.get(pk=import_file_id)
            organization = Organization.objects.get(pk=pk)
        except ImportFile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No import file found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'No organization found'
            }, status=status.HTTP_404_NOT_FOUND)

        result = Column.create_mappings(
            request.data.get('mappings', []),
            organization,
            request.user,
            import_file_id
        )

        if result:
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error'})
