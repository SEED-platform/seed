# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import json
import logging
import os
import subprocess

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from past.builtins import basestring
from rest_framework import status
from rest_framework.decorators import api_view

from seed import tasks
from seed.celery import app
from seed.data_importer.models import ImportFile, ImportRecord
from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm, requires_superuser
from seed.utils.api import api_endpoint
from seed.views.users import _get_js_role

_log = logging.getLogger(__name__)


def angular_js_tests(request):
    """Jasmine JS unit test code covering AngularJS unit tests"""
    debug = settings.DEBUG
    return render(request, 'seed/jasmine_tests/AngularJSTests.html', locals())


def _get_default_org(user):
    """Gets the default org for a user and returns the id, name, and
    role_level. If no default organization is set for the user, the first
    organization the user has access to is set as default if it exists.

    :param user: the user to get the default org
    :returns: tuple (Organization id, Organization name, OrganizationUser role)
    """
    org = user.default_organization
    # check if user is still in the org, i.e., they weren't removed from their
    # default org or did not have a set org and try to set the first one
    if not org or not user.orgs.exists():
        org = user.orgs.first()
        user.default_organization = org
        user.save()
    if org:
        org_id = org.pk
        org_name = org.name
        ou = user.organizationuser_set.filter(organization=org).first()
        # parent org owner has no role (None) yet has access to the sub-org
        org_user_role = _get_js_role(ou.role_level) if ou else ""
        return org_id, org_name, org_user_role
    else:
        return "", "", ""


@login_required
def home(request):
    """the main view for the app
        Sets in the context for the django template:

        * **app_urls**: a json object of all the URLs that is loaded in the JS global namespace
        * **username**: the request user's username (first and last name)
    """
    username = request.user.first_name + " " + request.user.last_name
    initial_org_id, initial_org_name, initial_org_user_role = _get_default_org(
        request.user
    )
    debug = settings.DEBUG
    return render(request, 'seed/index.html', locals())


@api_endpoint
@ajax_request
@api_view(['GET'])
def celery_queue(request):
    """
    Returns the number of running and queued celery tasks. This action can only be performed by superusers

    Returns::

        {
            'active': {'total': n, 'tasks': []}, // Tasks that are currently being executed
            'reserved': {'total': n, 'tasks': []}, // Tasks waiting to be executed
            'scheduled': {'total': n, 'tasks': []}, // Tasks reserved by the worker when they have an eta or countdown
            'maxConcurrency': The maximum number of active tasks
        }
    """
    if not requires_superuser(request):
        return JsonResponse({
            'status': 'error',
            'message': 'request is restricted to superusers'
        }, status=status.HTTP_403_FORBIDDEN)

    celery_tasks = app.control.inspect()
    results = {}

    methods = ('active', 'reserved', 'scheduled', 'stats')
    for method in methods:
        result = getattr(celery_tasks, method)()
        if result is None or 'error' in result:
            results[method] = 'Error'
            return
        for worker, response in result.items():
            if method == 'stats':
                results['maxConcurrency'] = response['pool']['max-concurrency']
            else:
                if response is not None:
                    total = len(response)
                    results[method] = {'total': total}
                    if total > 0:
                        results[method]['tasks'] = list(set([t['name'] for t in response]))
                else:
                    results[method] = {'total': 0}

    return JsonResponse(results)


@api_endpoint
@ajax_request
@api_view(['GET'])
def version(request):
    """
    Returns the SEED version and current git sha
    """
    manifest_path = os.path.dirname(
        os.path.realpath(__file__)) + '/../../package.json'
    with open(manifest_path, encoding='utf-8') as package_json:
        manifest = json.load(package_json)

    sha = subprocess.check_output(
        ['git', 'rev-parse', '--short=9', 'HEAD']).strip()

    return JsonResponse({
        'version': manifest['version'],
        'sha': sha.decode('utf-8')
    })


def error404(request, exception):
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Endpoint could not be found",
        }, status=status.HTTP_404_NOT_FOUND)
    else:
        return redirect('/app/#?http_error=404')


def error500(request):
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Internal server error",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return redirect('/app/#?http_error=500')


# @api_view(['POST'])  # do not add api_view on this because this is public and adding it will
# require authentication for some reason.
@ajax_request
def public_search(request):
    """
    The public API unauthenticated endpoint
    """
    # orgs = search.get_orgs_w_public_fields()
    return JsonResponse({
        'status': 'error',
        'message': 'this is not enabled yet'
    })


@ajax_request
@login_required
@api_view(['GET'])
def get_default_building_detail_columns(request):
    """Get default columns for building detail view.

    front end is expecting a JSON object with an array of field names

    Returns::

        {
            "columns": ["project_id", "name", "gross_floor_area"]
        }
    """
    columns = request.user.default_building_detail_custom_columns

    if columns == '{}' or isinstance(columns, dict):
        # Return empty result, telling the FE to show all.
        columns = []
    if isinstance(columns, basestring):
        # PostgreSQL 9.1 stores JSONField as unicode
        columns = json.loads(columns)

    return JsonResponse({
        'columns': columns,
    })


def _set_default_columns_by_request(body, user, field):
    """sets the default value for the user's default_custom_columns"""
    columns = body['columns']
    show_shared_buildings = body.get('show_shared_buildings')
    setattr(user, field, columns)
    if show_shared_buildings is not None:
        user.show_shared_buildings = show_shared_buildings
    user.save()
    return {}


@ajax_request
@login_required
@api_view(['POST'])
def set_default_columns(request):
    body = request.data
    return JsonResponse(
        _set_default_columns_by_request(body, request.user, 'default_custom_columns')
    )


@ajax_request
@login_required
@api_view(['POST'])
def set_default_building_detail_columns(request):
    body = request.data
    return JsonResponse(
        _set_default_columns_by_request(body, request.user,
                                        'default_building_detail_custom_columns')
    )


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
@api_view(['DELETE'])
def delete_file(request):
    """
    Deletes an ImportFile from a dataset.

    Payload::

        {
            "file_id": "ImportFile id",
            "organization_id": "current user organization id as integer"
        }

    Returns::

        {
            'status': 'success' or 'error',
            'message': 'error message, if any'
        }
    """
    if request.method != 'DELETE':
        return JsonResponse({
            'status': 'error',
            'message': 'only HTTP DELETE allowed',
        })
    body = request.data
    file_id = body.get('file_id', '')
    import_file = ImportFile.objects.get(pk=file_id)
    d = ImportRecord.objects.filter(
        super_organization_id=body['organization_id'],
        pk=import_file.import_record.pk
    )
    # check if user has access to the dataset
    if not d.exists():
        return JsonResponse({
            'status': 'error',
            'message': 'user does not have permission to delete file',
        })

    # Note that the file itself is not deleted, it remains on the disk
    import_file.delete()
    return JsonResponse({'status': 'success'})


@api_endpoint
@ajax_request
@login_required
@permission_required('seed.can_access_admin')
@api_view(['DELETE'])
def delete_organization_inventory(request):
    """
    Starts a background task to delete all properties & taxlots
    in an org.

    :DELETE: Expects 'org_id' for the organization.

    Returns::

        {
            'status': 'success' or 'error',
            'progress_key': ID of background job, for retrieving job progress
        }
    """
    org_id = request.query_params.get('organization_id', None)
    return JsonResponse(tasks.delete_organization_inventory(org_id))
