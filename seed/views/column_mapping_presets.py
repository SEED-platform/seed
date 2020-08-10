# !/usr/bin/env python
# encoding: utf-8

from django.http import JsonResponse

from rest_framework.decorators import action
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    Column,
    ColumnMappingProfile,
    Organization,
)
from seed.serializers.column_mapping_profiles import ColumnMappingProfileSerializer
from seed.utils.api import api_endpoint_class

from rest_framework.viewsets import ViewSet
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK


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
            profile_types = request.GET.getlist('profile_type')
            profile_types = [ColumnMappingProfile.get_profile_type(pt) for pt in profile_types]
            filter_params = {'organizations__pk': request.query_params.get('organization_id', None)}
            if profile_types:
                filter_params['profile_type__in'] = profile_types
            presets = ColumnMappingProfile.objects.filter(**filter_params)
            data = [ColumnMappingProfileSerializer(p).data for p in presets]

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
            preset = ColumnMappingProfile.objects.get(pk=pk)
        except ColumnMappingProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'data': 'No preset with given id'
            }, status=HTTP_400_BAD_REQUEST)

        if preset.profile_type == ColumnMappingProfile.BUILDINGSYNC_DEFAULT:
            return JsonResponse({
                'status': 'error',
                'data': 'Default BuildingSync presets are not editable'
            }, status=HTTP_400_BAD_REQUEST)

        updated_name, updated_mappings = request.data.get('name'), request.data.get('mappings')

        # update the name
        if updated_name is not None:
            preset.name = updated_name

        # update the mappings according to the preset type
        if updated_mappings is not None:
            if preset.profile_type == ColumnMappingProfile.BUILDINGSYNC_CUSTOM:
                # only allow these updates to the mappings
                # - changing the to_field or from_units
                # - removing mappings
                original_mappings_dict = {m['from_field']: m.copy() for m in preset.mappings}
                final_mappings = []
                for updated_mapping in updated_mappings:
                    from_field = updated_mapping['from_field']
                    original_mapping = original_mappings_dict.get(from_field)
                    if original_mapping is not None:
                        original_mapping['to_field'] = updated_mapping['to_field']
                        original_mapping['from_units'] = updated_mapping['from_units']
                        final_mappings.append(original_mapping)
                        del original_mappings_dict[from_field]

                preset.mappings = final_mappings
            elif updated_mappings:
                # indiscriminantly update the mappings
                preset.mappings = updated_mappings

        preset.save()
        return JsonResponse({
            'status': 'success',
            'data': ColumnMappingProfileSerializer(preset).data,
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
            # verify the org exists then validate and create the preset
            Organization.objects.get(pk=org_id)

            preset_data = request.data
            preset_data['organizations'] = [org_id]
            ser_preset = ColumnMappingProfileSerializer(data=preset_data)
            if ser_preset.is_valid():
                preset = ser_preset.save()
                response_status = 'success'
                response_data = ColumnMappingProfileSerializer(preset).data
                response_code = HTTP_200_OK
            else:
                response_status = 'error'
                response_data = ser_preset.errors
                response_code = HTTP_400_BAD_REQUEST

            return JsonResponse({
                'status': response_status,
                'data': response_data,
            }, status=response_code)
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
            preset = ColumnMappingProfile.objects.get(pk=pk)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)

        if preset.profile_type == ColumnMappingProfile.BUILDINGSYNC_DEFAULT:
            return JsonResponse({
                'status': 'error',
                'data': 'Not allowed to edit default BuildingSync presets'
            }, status=HTTP_400_BAD_REQUEST)
        else:
            preset.delete()
            return JsonResponse({
                'status': 'success',
                'data': "Successfully deleted",
            })

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
