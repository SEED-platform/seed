# !/usr/bin/env python
# encoding: utf-8

from django.http import JsonResponse

from drf_yasg.utils import swagger_auto_schema

from rest_framework.decorators import action
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.models import (
    Column,
    ColumnMappingProfile,
)
from seed.serializers.column_mapping_profiles import ColumnMappingProfileSerializer
from seed.utils.api import api_endpoint_class, OrgMixin
from seed.utils.api_schema import AutoSchemaHelper

from rest_framework.viewsets import ViewSet
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK

mappings_description = (
    "Each object in mappings must be in particular format:\n"
    "to_field: [string of Display Name of target Column]\n"
    "from_field: [string EXACTLY matching a header from an import file]\n"
    "from_units: [one of the following:"
    "'ft&#42;&#42;2' 'm&#42;&#42;2' 'kBtu/ft&#42;&#42;2/year' 'kWh/m&#42;&#42;2/year' 'GJ/m&#42;&#42;2/year' "
    "'MJ/m&#42;&#42;2/year' 'kBtu/m&#42;&#42;2/year']\n "
    "to_table_name: [one of the following: 'TaxLotState' 'PropertyState']"
)


class ColumnMappingProfileViewSet(OrgMixin, ViewSet):
    permission_classes = (SEEDOrgPermissions,)
    # req by SEEDOrgPermissions, but currently not used by any methods.
    queryset = ColumnMappingProfile.objects.none()

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id"
        )],
        request_body=AutoSchemaHelper.schema_factory(
            {'profile_type': ['string']},
            description="Possible Types: 'Normal', 'BuildingSync Default', BuildingSync Custom'"
        )
    )
    @api_endpoint_class
    @action(detail=False, methods=['POST'])  # POST in order to provide array/list
    def filter(self, request):
        """
        Retrieves all profiles for an organization.
        """
        try:
            profile_types = request.data.get('profile_type', [])
            profile_types = [ColumnMappingProfile.get_profile_type(pt) for pt in profile_types]
            filter_params = {'organizations__pk': self.get_organization(request, True).id}
            if profile_types:
                filter_params['profile_type__in'] = profile_types
            profiles = ColumnMappingProfile.objects.filter(**filter_params)
            data = [ColumnMappingProfileSerializer(p).data for p in profiles]

            return JsonResponse({
                'status': 'success',
                'data': data,
            })
        except Exception as e:
            raise e
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id"
        )],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'mappings': [{
                    'to_field': 'string',
                    'from_field': 'string',
                    'from_units': 'string',
                    'to_table_name': 'string',
                }]
            },
            description="Optional 'name' or 'mappings'.\n" + mappings_description
        )
    )
    @api_endpoint_class
    def update(self, request, pk=None):
        """
        Updates a profile given appropriate request data. The body should contain
        only valid fields for ColumnMappingProfile objects.
        """
        org_id = self.get_organization(request, True).id
        try:
            profile = ColumnMappingProfile.objects.get(organizations__pk=org_id, pk=pk)
        except ColumnMappingProfile.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'data': 'No profile with given id'
            }, status=HTTP_400_BAD_REQUEST)

        if profile.profile_type == ColumnMappingProfile.BUILDINGSYNC_DEFAULT:
            return JsonResponse({
                'status': 'error',
                'data': 'Default BuildingSync profile are not editable'
            }, status=HTTP_400_BAD_REQUEST)

        updated_name, updated_mappings = request.data.get('name'), request.data.get('mappings')

        # update the name
        if updated_name is not None:
            profile.name = updated_name

        # update the mappings according to the profile type
        if updated_mappings is not None:
            if profile.profile_type == ColumnMappingProfile.BUILDINGSYNC_CUSTOM:
                # only allow these updates to the mappings
                # - changing the to_field or from_units
                # - removing mappings
                original_mappings_dict = {m['from_field']: m.copy() for m in profile.mappings}
                final_mappings = []
                for updated_mapping in updated_mappings:
                    from_field = updated_mapping['from_field']
                    original_mapping = original_mappings_dict.get(from_field)
                    if original_mapping is not None:
                        original_mapping['to_field'] = updated_mapping['to_field']
                        original_mapping['from_units'] = updated_mapping['from_units']
                        final_mappings.append(original_mapping)
                        del original_mappings_dict[from_field]

                profile.mappings = final_mappings
            elif updated_mappings:
                # indiscriminantly update the mappings
                profile.mappings = updated_mappings

        profile.save()
        return JsonResponse({
            'status': 'success',
            'data': ColumnMappingProfileSerializer(profile).data,
        })

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id"
        )],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'name': 'string',
                'mappings': [{
                    'to_field': 'string',
                    'from_field': 'string',
                    'from_units': 'string',
                    'to_table_name': 'string',
                }]
            },
            description=mappings_description,
            required=['name', 'mappings']
        )
    )
    @api_endpoint_class
    def create(self, request, pk=None):
        """
        Creates a new profile given appropriate request data. The body should
        contain only valid fields for ColumnMappingProfile objects.
        """
        org_id = self.get_organization(request, True).id
        try:
            profile_data = request.data
            profile_data['organizations'] = [org_id]
            ser_profile = ColumnMappingProfileSerializer(data=profile_data)
            if ser_profile.is_valid():
                profile = ser_profile.save()
                response_status = 'success'
                response_data = ColumnMappingProfileSerializer(profile).data
                response_code = HTTP_200_OK
            else:
                response_status = 'error'
                response_data = ser_profile.errors
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

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id"
        )]
    )
    @api_endpoint_class
    def destroy(self, request, pk=None):
        """
        Deletes a specific profile.
        """
        org_id = self.get_organization(request, True).id
        try:
            profile = ColumnMappingProfile.objects.get(organizations__pk=org_id, pk=pk)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'data': str(e),
            }, status=HTTP_400_BAD_REQUEST)

        if profile.profile_type == ColumnMappingProfile.BUILDINGSYNC_DEFAULT:
            return JsonResponse({
                'status': 'error',
                'data': 'Not allowed to edit default BuildingSync profiles'
            }, status=HTTP_400_BAD_REQUEST)
        else:
            profile.delete()
            return JsonResponse({
                'status': 'success',
                'data': "Successfully deleted",
            })

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field(
            required=False,
            description="Optional org id which overrides the users (default) current org id"
        )],
        request_body=AutoSchemaHelper.schema_factory(
            {'headers': ['string']},
            description="Raw headers - the exact headers for columns in an import file.",
            required=['headers']
        )
    )
    @api_endpoint_class
    @action(detail=False, methods=['POST'])
    def suggestions(self, request):
        """
        Retrieves suggestions given raw column headers.
        """
        try:
            org_id = self.get_organization(request, True).id
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
