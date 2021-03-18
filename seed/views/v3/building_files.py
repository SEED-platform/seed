# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import os
import zipfile
from tempfile import NamedTemporaryFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status
from rest_framework.parsers import MultiPartParser

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import BuildingFile, Cycle
from seed.serializers.building_file import BuildingFileSerializer
from seed.serializers.properties import PropertyViewAsStateSerializer
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgReadOnlyModelViewSet


@method_decorator(swagger_auto_schema_org_query_param, name='list')
@method_decorator(swagger_auto_schema_org_query_param, name='retrieve')
class BuildingFileViewSet(SEEDOrgReadOnlyModelViewSet):
    model = BuildingFile
    orgfilter = 'property_state__organization'
    parser_classes = (MultiPartParser,)
    pagination_class = None

    def get_serializer_class(self):
        if self.action == 'create':
            # pass "empty" serializer for Swagger page
            return serializers.Serializer
        return BuildingFileSerializer

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle_id',
                required=True,
                description='Cycle to upload to'
            ),
            AutoSchemaHelper.upload_file_field(
                'file',
                required=True,
                description='File to upload',
            ),
            AutoSchemaHelper.form_string_field(
                'file_type',
                required=True,
                description='Either "Unknown", "BuildingSync" or "HPXML"',
            ),
        ],
    )
    @has_perm_class('can_modify_data')
    def create(self, request):
        """
        Create a new property from a building file
        """
        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': 'Must pass file in as a Multipart/Form post'
            })

        the_file = request.data['file']
        file_type = BuildingFile.str_to_file_type(request.data.get('file_type', 'Unknown'))

        organization_id = self.get_organization(self.request)
        cycle = request.query_params.get('cycle_id', None)

        if not cycle:
            return JsonResponse({
                'success': False,
                'message': 'Cycle ID is not defined'
            })
        else:
            cycle = Cycle.objects.get(pk=cycle)

        # figure out if file is xml or zip
        the_filename = the_file._get_name()
        tmp_filename, file_extension = os.path.splitext(the_filename)
        # initialize
        p_status = True
        property_state = True
        messages = {'errors': [], 'warnings': []}

        if file_extension == '.zip':
            # ZIP FILE, extract and process files one by one
            # print("This file is a ZIP")

            with zipfile.ZipFile(the_file, "r", zipfile.ZIP_STORED) as openzip:
                filelist = openzip.infolist()
                for f in filelist:
                    # print("FILE: {}".format(f.filename))
                    # process xml files
                    if '.xml' in f.filename and '__MACOSX' not in f.filename:
                        # print("PROCESSING file: {}".format(f.filename))
                        data_file = NamedTemporaryFile()
                        data_file.write(openzip.read(f))
                        data_file.seek(0)
                        size = os.path.getsize(data_file.name)
                        content_type = 'text/xml'
                        # print("DATAFILE:")
                        # print(data_file)
                        a_file = InMemoryUploadedFile(
                            data_file, 'data_file', f.filename, content_type,
                            size, charset=None)

                        building_file = BuildingFile.objects.create(
                            file=a_file,
                            filename=f.filename,
                            file_type=file_type,
                        )
                        p_status_tmp, property_state_tmp, property_view, messages_tmp = building_file.process(organization_id, cycle)
                        # print('messages_tmp: ')
                        # print(messages_tmp)

                        # append errors to overall messages
                        for i in messages_tmp['errors']:
                            messages['errors'].append(f.filename + ": " + i)
                        for i in messages_tmp['warnings']:
                            messages['warnings'].append(f.filename + ": " + i)

                        if not p_status_tmp:
                            # capture error
                            p_status = p_status_tmp
                        else:
                            # capture a real property_state (not None)
                            property_state = property_state_tmp

        else:
            # just an XML
            building_file = BuildingFile.objects.create(
                file=the_file,
                filename=the_file.name,
                file_type=file_type,
            )

            p_status, property_state, property_view, messages = building_file.process(organization_id, cycle)

        if p_status and property_state:
            if len(messages['warnings']) > 0:
                return JsonResponse({
                    'success': True,
                    'status': 'success',
                    'message': {'warnings': messages['warnings']},
                    'data': {
                        'property_view': PropertyViewAsStateSerializer(property_view).data,
                        # 'property_state': PropertyStateWritableSerializer(property_state).data,
                    },
                })
            else:
                return JsonResponse({
                    'success': True,
                    'status': 'success',
                    'message': {'warnings': []},
                    'data': {
                        'property_view': PropertyViewAsStateSerializer(property_view).data,
                        # 'property_state': PropertyStateWritableSerializer(property_state).data,
                    },
                })
        else:
            return JsonResponse({
                'success': False,
                'status': 'error',
                'message': messages
            }, status=status.HTTP_400_BAD_REQUEST)
