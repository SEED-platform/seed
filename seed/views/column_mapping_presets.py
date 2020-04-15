# !/usr/bin/env python
# encoding: utf-8

from django.core.exceptions import FieldDoesNotExist
from django.http import JsonResponse

from rest_framework.decorators import action
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    Column,
    ColumnMappingPreset,
    Organization,
)
from seed.serializers.column_mapping_presets import ColumnMappingPresetSerializer
from seed.utils.api import api_endpoint_class

from rest_framework.viewsets import ViewSet
from rest_framework.status import HTTP_400_BAD_REQUEST


class ColumnMappingPresetViewSet(ViewSet):
    @api_endpoint_class
    @has_perm_class('requires_member')
    def list(self, request):
        """
        Retrieves all presets for an organization.
        parameters:
           - name: organization_id
             description: The organization_id for this user's organization
             required: true (at least, nothing will be returned if not provided)
             paramType: query
        """
        try:
            org_id = request.query_params.get('organization_id', None)
            presets = ColumnMappingPreset.objects.filter(organizations__pk=org_id)
            data = [ColumnMappingPresetSerializer(p).data for p in presets]

            return JsonResponse({
                'status': 'success',
                'data': data,
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)

    @api_endpoint_class
    @has_perm_class('can_modify_data')
    def update(self, request, pk=None):
        """
        Updates a preset given appropriate request data. The body should contain
        only valid fields for ColumnMappingPreset objects.
        parameters:
            - name: pk
              description: ID of Preset
              required: true
              paramType: path
            - name: name
              description: Name of preset
              required: false
              paramType: body
            - name: mappings
              description: List of dictionaries
              required: false
              paramType: body
        """
        try:
            updated = ColumnMappingPreset.objects.filter(pk=pk).update(**request.data)
        except FieldDoesNotExist as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e),
            }, status=HTTP_400_BAD_REQUEST)

        if updated:
            preset = ColumnMappingPreset.objects.get(pk=pk)
            status = 'success'
            data = ColumnMappingPresetSerializer(preset).data
        else:
            status = 'error'
            data = "Column Mapping Preset not updated."

        return JsonResponse({
            'status': status,
            'data': data,
        })

    @api_endpoint_class
    @has_perm_class('can_modify_data')
    def create(self, request, pk=None):
        """
        Creates a new preset given appropriate request data. The body should
        contain only valid fields for ColumnMappingPreset objects.
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: name
              description: Name of preset
              required: false
              paramType: body
            - name: mappings
              description: List of dictionaries
              required: false
              paramType: body
        """
        org_id = request.query_params.get('organization_id', None)
        try:
            org = Organization.objects.get(pk=org_id)
            preset = org.columnmappingpreset_set.create(**request.data)

            return JsonResponse({
                'status': 'success',
                'data': ColumnMappingPresetSerializer(preset).data,
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)

    @api_endpoint_class
    @has_perm_class('can_modify_data')
    def delete(self, request, pk=None):
        """
        Deletes a specific preset.
        parameters:
            - name: pk
              description: ID of Preset
              required: true
              paramType: path
        """
        try:
            ColumnMappingPreset.objects.get(pk=pk).delete()

            return JsonResponse({
                'status': 'success',
                'data': "Successfully deleted",
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)

    @api_endpoint_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['POST'])
    def suggestions(self, request):
        """
        Retrieves suggestions given raw column headers.
        parameters:
           - headers:---------------------------------------------------------------------------------------------------------------------------
           - name: organization_id
             description: The organization_id for this user's organization
             required: true (at least, nothing will be returned if not provided)
             paramType: query
        """
        try:
            org_id = request.query_params.get('organization_id', None)
            raw_headers = request.data.get('headers', [])

            suggested_mappings = mapper.build_column_mapping(
                raw_headers,
                Column.retrieve_all_by_tuple(org_id),
                previous_mapping=None,
                map_args=None,
                thresh=80  # percentage match that we require. 80% is random value for now.
            )
            # replace None with empty string for column names and PropertyState for tables
            # TODO #239: Move this fix to build_column_mapping
            for m in suggested_mappings:
                table, destination_field, _confidence = suggested_mappings[m]
                if destination_field is None:
                    suggested_mappings[m][1] = ''

            # Fix the table name, eventually move this to the build_column_mapping
            for m in suggested_mappings:
                table, _destination_field, _confidence = suggested_mappings[m]
                # Do not return the campus, created, updated fields... that is force them to be in the property state
                if not table or table == 'Property':
                    suggested_mappings[m][0] = 'PropertyState'
                elif table == 'TaxLot':
                    suggested_mappings[m][0] = 'TaxLotState'

            return JsonResponse({
                'status': 'success',
                'data': suggested_mappings,
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)
