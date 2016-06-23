# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import datetime
import json
import logging
import os
import subprocess
import uuid
from collections import defaultdict

from dateutil.parser import parse
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import DefaultStorage
from django.db.models import Q
from django.http import HttpResponseBadRequest
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from seed import models, tasks
from seed.audit_logs.models import AuditLog
from seed.common import mapper as simple_mapper
from seed.common import views as vutil
from seed.data_importer.models import ImportFile, ImportRecord, ROW_DELIMITER
from seed.decorators import ajax_request, get_prog_key, require_organization_id
from seed.lib.exporter import Exporter
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    get_column_mapping,
    save_snapshot_match,
    BuildingSnapshot,
    Column,
    ColumnMapping,
    ProjectBuilding,
    get_ancestors,
    unmatch_snapshot_tree as unmatch_snapshot,
    CanonicalBuilding,
    ASSESSED_BS,
    PORTFOLIO_BS,
    GREEN_BUTTON_BS,
)
from seed.tasks import (
    map_data,
    remap_data,
    match_buildings,
    save_raw_data as task_save_raw,
)
from seed.utils.api import api_endpoint
from seed.utils.buildings import (
    get_columns as utils_get_columns,
    get_buildings_for_user_count
)
from seed.utils.cache import get_cache, set_cache
from seed.utils.generic import median, round_down_hundred_thousand
from seed.utils.mapping import get_mappable_types, get_mappable_columns
from seed.utils.projects import (
    get_projects,
)
from seed.utils.time import convert_to_js_timestamp
from seed.views.accounts import _get_js_role
from .. import search

from rest_framework.decorators import api_view
from rest_framework import serializers, viewsets
from rest_framework.response import Response
from django.http import HttpResponse

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]

_log = logging.getLogger(__name__)


class DatasetViewSet(viewsets.ViewSet):
    @require_organization_id
    @api_endpoint
    @ajax_request
    @login_required
    def list(self, request):
        """
        Retrieves all datasets for the user's organization.

        :GET: Expects 'organization_id' of org to retrieve datasets from
            in query string.

        Returns::

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
        """
        from seed.models import obj_to_dict

        org = Organization.objects.get(pk=request.GET['organization_id'])
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

        return {
            'status': 'success',
            'datasets': datasets,
        }

    @api_endpoint
    @ajax_request
    @login_required
    @has_perm('can_modify_data')
    def update(self, request, pk=None):
        """
        Updates the name of a dataset.

        Payload::

            {
                'dataset': {
                    'id': The ID of the Import Record,
                    'name': The new name for the ImportRecord
                }
            }

        Returns::

            {
                'status': 'success' or 'error',
                'message': 'error message, if any'
            }
        """
        body = json.loads(request.body)
        orgs = request.user.orgs.all()
        # check if user has access to the dataset
        d = ImportRecord.objects.filter(
            super_organization__in=orgs, pk=body['dataset']['id']
        )
        if not d.exists():
            return {
                'status': 'error',
                'message': 'user does not have permission to update dataset',
            }
        d = d[0]
        d.name = body['dataset']['name']
        d.save()
        return {
            'status': 'success',
        }

    @api_endpoint
    @ajax_request
    @login_required
    def retrieve(self, request, pk=None):
        """
        Retrieves ImportFile objects for one ImportRecord.

        :GET: Expects dataset_id for an ImportRecord in the query string.

        Returns::

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
        """
        from seed.models import obj_to_dict

        dataset_id = request.GET.get('dataset_id', '')
        orgs = request.user.orgs.all()
        # check if user has access to the dataset
        d = ImportRecord.objects.filter(
            super_organization__in=orgs, pk=dataset_id
        )
        if d.exists():
            d = d[0]
        else:
            return {
                'status': 'success',
                'dataset': {},
            }

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

        return {
            'status': 'success',
            'dataset': dataset,
        }

    @api_endpoint
    @ajax_request
    @login_required
    @has_perm('requires_member')
    def destroy(self, request, pk=None):
        """
        Deletes all files from a dataset and the dataset itself.

        :DELETE: Expects organization id and dataset id.

        Payload::

            {
                "dataset_id": 1,
                "organization_id": 1
            }

        Returns::

            {
                'status': 'success' or 'error',
                'message': 'error message, if any'
            }
        """
        body = json.loads(request.body)
        dataset_id = body.get('dataset_id', '')
        organization_id = body.get('organization_id')
        # check if user has access to the dataset
        d = ImportRecord.objects.filter(
            super_organization_id=organization_id, pk=dataset_id
        )
        if not d.exists():
            return {
                'status': 'error',
                'message': 'user does not have permission to delete dataset',
            }
        d = d[0]
        d.delete()
        return {
            'status': 'success',
        }

    @api_endpoint
    @ajax_request
    @login_required
    @has_perm('can_modify_data')
    def create(self, request):
        """
        Creates a new empty dataset (ImportRecord).

        Payload::

            {
                "name": Name of new dataset, e.g. "2013 city compliance dataset"
                "organization_id": ID of the org this dataset belongs to
            }

        Returns::

            {
                'status': 'success',
                'id': The ID of the newly-created ImportRecord,
                'name': The name of the newly-created ImportRecord
            }
        """
        body = json.loads(request.body)

        # validate inputs
        invalid = vutil.missing_request_keys(['organization_id'], body)
        if invalid:
            return vutil.api_error(invalid)
        invalid = vutil.typeof_request_values({'organization_id': int}, body)
        if invalid:
            return vutil.api_error(invalid)

        org_id = int(body['organization_id'])

        try:
            _log.info("create_dataset: getting Organization for id=({})".format(org_id))
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

        return {
            'status': 'success',
            'id': record.pk,
            'name': record.name,
        }
