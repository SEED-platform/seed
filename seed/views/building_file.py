# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.http import JsonResponse
from rest_framework import status

from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import BuildingFile, Cycle
from seed.serializers.building_file import BuildingFileSerializer
from seed.serializers.properties import PropertyStateWritableSerializer
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
              enum: ["Unknown", "BuildingSync", "GeoJSON", "HPXML"]
              required: true
            - name: file
              description: In-memory file object
              required: true
              type: file
        """
        if len(request.FILES) == 0:
            return JsonResponse({
                'success': False,
                'message': "Must pass file in as a Multipart/Form post"
            })

        the_file = request.data['file']
        file_type = BuildingFile.str_to_file_type(request.data.get('file_type', 'Unknown'))
        organization_id = request.data['organization_id']
        cycle = request.data.get('cycle_id', None)

        if not cycle:
            return JsonResponse({
                'success': False,
                'message': "Cycle ID is not defined"
            })
        else:
            cycle = Cycle.objects.get(pk=cycle)

        building_file = BuildingFile.objects.create(
            file=the_file,
            filename=the_file.name,
            file_type=file_type,
        )

        p_status, property_state, messages = building_file.process(organization_id, cycle)
        if p_status and property_state:
            return JsonResponse({
                "status": "success",
                "message": "successfully imported file",
                "data": {
                    "property_state": PropertyStateWritableSerializer(property_state).data,
                },
            })
        else:
            return JsonResponse({
                "status": "error",
                "message": "Could not process building file with messages {}".format(messages)
            }, status=status.HTTP_400_BAD_REQUEST)
