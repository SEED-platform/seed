# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import datetime
import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from rest_framework import viewsets

from seed.data_importer.models import ImportRecord
from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models import BuildingSnapshot
from seed.utils.api import api_endpoint_class
from seed.utils.time import convert_to_js_timestamp

_log = logging.getLogger(__name__)


class DatasetViewSet(LoginRequiredMixin, viewsets.ViewSet):
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all datasets for the user's organization.

        Until we can get the nested JSON response working, here's what we're sending back as a response:

           {
                'status': 'success',
                'datasets':  [
                    {
                        'name': Name of ImportRecord,
                        'number_of_buildings': Total number of buildings in all ImportFiles,
                        'id': ID of ImportRecord,
                        'updated_at': Timestamp of when ImportRecord was last modified,
                        'last_modified_by': Email address of user making last change,
                        'importfiles': [
                            {
                                'name': Name of associated ImportFile, e.g. 'buildings.csv',
                                'number_of_buildings': Count of buildings in this file,
                                'number_of_mappings': Number of mapped headers to fields,
                                'number_of_cleanings': Number of fields cleaned,
                                'source_type': Type of file (see source_types),
                                'id': ID of ImportFile (needed for most operations)
                            }
                        ],
                        ...
                    },
                    ...
                ]
            }
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        type:
            status:
                required: true
                type: string
                description: "'success' if the call succeeds"
            datasets:
                required: true
                description: The datasets
                type: object
        """

        org_id = request.query_params.get('organization_id', None)
        from seed.models import obj_to_dict
        org = Organization.objects.get(pk=org_id)
        datasets = []
        for d in ImportRecord.objects.filter(super_organization=org):
            importfiles = [obj_to_dict(f) for f in d.files]
            dataset = obj_to_dict(d)
            dataset['importfiles'] = importfiles
            if d.last_modified_by:
                dataset['last_modified_by'] = d.last_modified_by.email
            dataset['number_of_buildings'] = BuildingSnapshot.objects.filter(
                import_file__in=d.files,
                canonicalbuilding__active=True,
            ).count()
            dataset['updated_at'] = convert_to_js_timestamp(d.updated_at)
            datasets.append(dataset)

        return HttpResponse(json.dumps({
            'status': 'success',
            'datasets': datasets,
        }))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def update(self, request, pk=None):
        """
            Updates the name of a dataset (ImportRecord).
            ---
            type:
                status:
                    required: true
                    type: string
                    description: either success or error
                message:
                    type: string
                    description: error message, if any
            parameter_strategy: replace
            parameters:
                - name: organization_id
                  description: "The organization_id"
                  required: true
                  paramType: query
                - name: new_dataset_name
                  description: "The new name for this dataset"
                  required: true
                  paramType: string
                - name: pk
                  description: "Primary Key"
                  required: true
                  paramType: path
        """

        organization_id = int(
            request.query_params.get('organization_id', None))
        dataset_id = pk
        name = request.data['new_dataset_name']

        # check if user has access to the dataset
        d = ImportRecord.objects.filter(
            super_organization_id=organization_id, pk=dataset_id
        )
        if not d.exists():
            return HttpResponse(json.dumps({
                'status': 'error',
                'message': 'user does not have permission to update dataset',
            }))
        d = d[0]
        d.name = name
        d.save()
        return HttpResponse(json.dumps({
            'status': 'success',
        }))

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
            Retrieves a dataset (ImportRecord).

            Until we can get the nested JSON response working, here's what we're sending back as a response:

            {
                'status': 'success',
                'dataset': {
                    'name': Name of ImportRecord,
                    'number_of_buildings': Total number of buildings in all ImportFiles for this dataset,
                    'id': ID of ImportRecord,
                    'updated_at': Timestamp of when ImportRecord was last modified,
                    'last_modified_by': Email address of user making last change,
                    'importfiles': [
                        {
                           'name': Name of associated ImportFile, e.g. 'buildings.csv',
                           'number_of_buildings': Count of buildings in this file,
                           'number_of_mappings': Number of mapped headers to fields,
                           'number_of_cleanings': Number of fields cleaned,
                           'source_type': Type of file (see source_types),
                           'id': ID of ImportFile (needed for most operations)
                        }
                     ],
                     ...
                },
                    ...
            }
            ---
            parameter_strategy: replace
            parameters:
                - name: organization_id
                  description: The organization_id
                  required: true
                  paramType: query
                - name: pk
                  description: "Primary Key"
                  required: true
                  paramType: path
        """

        organization_id = int(
            request.query_params.get('organization_id', None))
        dataset_id = pk

        from seed.models import obj_to_dict

        # check if user has access to the dataset
        d = ImportRecord.objects.filter(
            super_organization_id=organization_id, pk=dataset_id
        )
        if d.exists():
            d = d[0]
        else:
            return HttpResponse(json.dumps({
                'status': 'success',
                'dataset': {},
            }))

        dataset = obj_to_dict(d)
        importfiles = []
        for f in d.files:
            importfile = obj_to_dict(f)
            importfile['name'] = f.filename_only
            importfiles.append(importfile)

        dataset['importfiles'] = importfiles
        if d.last_modified_by:
            dataset['last_modified_by'] = d.last_modified_by.email
        dataset['number_of_buildings'] = BuildingSnapshot.objects.filter(
            import_file__in=d.files
        ).count()
        dataset['updated_at'] = convert_to_js_timestamp(d.updated_at)

        return HttpResponse(json.dumps({
            'status': 'success',
            'dataset': dataset,
        }))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def destroy(self, request, pk=None):
        """
            Deletes a dataset (ImportRecord).
            ---
            type:
                status:
                    required: true
                    type: string
                    description: either success or error
                message:
                    type: string
                    description: error message, if any
            parameter_strategy: replace
            parameters:
                - name: organization_id
                  description: The organization_id
                  required: true
                  paramType: query
                - name: pk
                  description: "Primary Key"
                  required: true
                  paramType: path
        """

        # body = request.data
        organization_id = int(
            request.query_params.get('organization_id', None))
        dataset_id = pk
        # check if user has access to the dataset
        d = ImportRecord.objects.filter(
            super_organization_id=organization_id, pk=dataset_id
        )
        if not d.exists():
            return HttpResponse(json.dumps({
                'status': 'error',
                'message': 'user does not have permission to delete dataset',
            }))
        d = d[0]
        d.delete()
        return HttpResponse(json.dumps({'status': 'success'}))

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('can_modify_data')
    def create(self, request):
        """
        Creates a new empty dataset (ImportRecord).
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            id:
                required: true
                type: integer
                description: primary key for the newly created dataset
            name:
                required: true
                type: string
                description: name of the newly created dataset
        parameters:
            - name: name
              description: The name of this dataset
              required: true
              paramType: string
            - name: organization_id
              description: The organization_id
              required: true
              paramType: query
        """

        body = request.data
        org_id = int(request.query_params.get('organization_id', None))

        try:
            _log.info(
                "create_dataset: getting Organization for id=({})".format(
                    org_id))
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return {"status": 'error',
                    'message': 'organization_id not provided'}
        record = ImportRecord.objects.create(
            name=body['name'],
            app="seed",
            start_time=datetime.datetime.now(),
            created_at=datetime.datetime.now(),
            last_modified_by=request.user,
            super_organization=org,
            owner=request.user,
        )

        return HttpResponse(json.dumps(
            {'status': 'success', 'id': record.pk, 'name': record.name}))
