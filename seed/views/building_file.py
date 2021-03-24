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
from rest_framework import status

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import BuildingFile, Cycle
from seed.serializers.building_file import BuildingFileSerializer
from seed.serializers.properties import PropertyViewAsStateSerializer
from seed.utils.viewsets import SEEDOrgReadOnlyModelViewSet


class BuildingFileViewSet(SEEDOrgReadOnlyModelViewSet):
    model = BuildingFile
    serializer_class = BuildingFileSerializer
    orgfilter = 'property_state__organization'

    # TODO: add the building_file serializer to this and override the methods (perform_create)

    @has_perm_class('can_modify_data')
    def create(self, request):
        """
        Does not work in Swagger!

        Create a new Property from a building file.
        ---
        consumes:
            - multipart/form-data
        parameters:
            - name: organization_id
              type: integer
              required: true
            - name: cycle_id
              type: integer
              required: true
            - name: file_type
              type: string
              enum: ["Unknown", "BuildingSync", "HPXML"]
              required: true
            - name: file
              description: In-memory file object
              required: true
              type: file
        """
        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': 'Must pass file in as a Multipart/Form post'
            })

        the_file = request.data['file']
        file_type = BuildingFile.str_to_file_type(request.data.get('file_type', 'Unknown'))

        organization_id = request.data['organization_id']
        cycle = request.data.get('cycle_id', None)

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
