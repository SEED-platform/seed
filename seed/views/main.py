# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import json
import logging
import os
import subprocess

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.storage import DefaultStorage
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view

from seed import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.decorators import (
    ajax_request, get_prog_key
)
from seed.lib.exporter import Exporter
from seed.lib.mappings import mapper as simple_mapper
from seed.lib.mappings import mapping_data
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.models import (
    Column,
    get_column_mapping,
)
from seed.utils.api import api_endpoint
from seed.views.users import _get_js_role
from .. import search

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]

_log = logging.getLogger(__name__)


def angular_js_tests(request):
    """Jasmine JS unit test code covering AngularJS unit tests"""
    return render(request, 'seed/jasmine_tests/AngularJSTests.html', locals())


def _get_default_org(user):
    """Gets the default org for a user and returns the id, name, and
    role_level. If no default organization is set for the user, the first
    organization the user has access to is set as default if it exists.

    :param user: the user to get the default org
    :returns: tuple (Organization id, Organization name, OrganizationUser role)
    """
    org = user.default_organization
    # check if user is still in the org, i.e. s/he wasn't removed from his/her
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
        * **AWS_UPLOAD_BUCKET_NAME**: S3 direct upload bucket
        * **AWS_CLIENT_ACCESS_KEY**: S3 direct upload client key
        * **FILE_UPLOAD_DESTINATION**: 'S3' or 'filesystem'
    """

    username = request.user.first_name + " " + request.user.last_name
    if 'S3' in settings.DEFAULT_FILE_STORAGE:
        FILE_UPLOAD_DESTINATION = 'S3'
        AWS_UPLOAD_BUCKET_NAME = settings.AWS_BUCKET_NAME
        AWS_CLIENT_ACCESS_KEY = settings.AWS_UPLOAD_CLIENT_KEY
    else:
        FILE_UPLOAD_DESTINATION = 'filesystem'

    initial_org_id, initial_org_name, initial_org_user_role = _get_default_org(
        request.user
    )

    return render(request, 'seed/index.html', locals())


@api_endpoint
@ajax_request
@api_view(['GET'])
def version(request):
    """
    Returns the SEED version and current git sha
    """
    manifest_path = os.path.dirname(
        os.path.realpath(__file__)) + '/../../package.json'
    with open(manifest_path) as package_json:
        manifest = json.load(package_json)

    sha = subprocess.check_output(
        ['git', 'rev-parse', '--short', 'HEAD']).strip()

    return JsonResponse({
        'version': manifest['version'],
        'sha': sha
    })


def error404(request):
    # Okay, this is a bit of a hack. Needed to move on.
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Endpoint could not be found",
        }, status=status.HTTP_404_NOT_FOUND)
    else:
        response = render(request, 'seed/404.html', {})
        response.status_code = 404
        return response


def error500(request):
    # Okay, this is a bit of a hack. Needed to move on.
    if '/api/' in request.path:
        return JsonResponse({
            "status": "error",
            "message": "Internal server error",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        response = render(request, 'seed/500.html', {})
        response.status_code = 500
        return response


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])
def export_buildings_download(request):
    """
    Provides the url to a building export file.

    Payload::

        {
            "export_id": export_id from export_buildings
        }

    Returns::

        {
            'success': True or False,
            'status': 'success or error',
            'message': 'error message, if any',
            'url': The url to the exported file.
        }
    """
    body = request.data
    export_id = body.get('export_id')

    # This is non-ideal, it is returning the directory/s3 key and assumes that
    # only one file lives in that directory. This should really just return the
    # file to be downloaded. Not sure we are doing multiple downloads at the
    # moment.
    export_subdir = Exporter.subdirectory_from_export_id(export_id)

    if 'S3' in settings.DEFAULT_FILE_STORAGE:
        keys = list(DefaultStorage().bucket.list(export_subdir))

        if not keys:
            return JsonResponse({
                'success': False,
                'status': 'working'
            })

        if len(keys) > 1:
            return JsonResponse({
                "success": False,
                "status": "error",
            })

        download_key = keys[0]
        download_url = download_key.generate_url(900)

        return JsonResponse({
            'success': True,
            "status": "success",
            "url": download_url
        })
    else:
        file_storage = DefaultStorage()

        try:
            files = file_storage.listdir(export_subdir)
        except OSError:
            # Likely scenario is that the file hasn't been written to disk yet.
            return JsonResponse({'success': False, 'status': 'working'})

        if not files:
            return JsonResponse({'success': False, 'status': 'error'})
        else:
            # get the first file in the directory -- which is the first entry
            # of the second part of the tuple
            file_name = os.path.join(export_subdir, files[1][0])

            if file_storage.exists(file_name):
                url = file_storage.url(file_name)
                return JsonResponse({
                    'success': True,
                    "status": "success",
                    "url": url
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Could not find file on server',
                    'status': 'error'
                })


# @api_view(['POST'])  # do not add api_view on this because this is public and adding it will
# require authentication for some reason.
@ajax_request
def public_search(request):
    """the public API unauthenticated endpoint

    see ``search_buildings`` for the non-public version
    """
    orgs = search.get_orgs_w_public_fields()
    search_results, building_count = search.search_public_buildings(
        request, orgs
    )
    search_results = search.remove_results_below_q_threshold(search_results)
    search_results = search.paginate_results(request, search_results)
    search_results = search.mask_results(search_results)
    return JsonResponse({
        'status': 'success',
        'buildings': search_results,
        'number_matching_search': building_count,
        'number_returned': len(search_results)
    })


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])
def search_buildings(request):
    """
    Retrieves a paginated list of CanonicalBuildings matching search params.

    Payload::

        {
            'q': a string to search on (optional),
            'show_shared_buildings': True to include buildings from other orgs in this user's org tree,
            'order_by': which field to order by (e.g. pm_property_id),
            'import_file_id': ID of an import to limit search to,
            'filter_params': {
                a hash of Django-like filter parameters to limit query.  See seed.search.filter_other_params.
                If 'project__slug' is included and set to a project's slug, buildings will include associated labels
                for that project.
            }
            'page': Which page of results to retrieve (default: 1),
            'number_per_page': Number of buildings to retrieve per page (default: 10),
        }

    Returns::

        {
            'status': 'success',
            'buildings': [
                {
                    all fields for buildings the request user has access to, e.g.:
                        'canonical_building': the CanonicalBuilding ID of the building,
                        'pm_property_id': ID of building (from Portfolio Manager),
                        'address_line_1': First line of building's address,
                        'property_name': Building's name, if any
                    ...
                }...
            ]
            'number_matching_search': Total number of buildings matching search,
            'number_returned': Number of buildings returned for this page
        }
    """
    params = search.parse_body(request)

    orgs = request.user.orgs.select_related('parent_org').all()
    parent_org = orgs[0].parent_org

    buildings_queryset = search.orchestrate_search_filter_sort(
        params=params,
        user=request.user,
    )

    below_threshold = (
        parent_org and parent_org.query_threshold and
        len(buildings_queryset) < parent_org.query_threshold
    )

    buildings, building_count = search.generate_paginated_results(
        buildings_queryset,
        number_per_page=params['number_per_page'],
        page=params['page'],
        # Generally just orgs, sometimes all orgs with public fields.
        whitelist_orgs=orgs,
        below_threshold=below_threshold,
        matching=False
    )

    return JsonResponse({
        'status': 'success',
        'buildings': buildings,
        'number_matching_search': building_count,
        'number_returned': len(buildings)
    })


@ajax_request
@login_required
@api_view(['GET'])
def get_default_columns(request):
    """Get default columns for building list view.

    front end is expecting a JSON object with an array of field names

    Returns::

        {
            "columns": ["project_id", "name", "gross_floor_area"]
        }
    """
    columns = request.user.default_custom_columns

    if columns == '{}' or isinstance(columns, dict):
        columns = DEFAULT_CUSTOM_COLUMNS
    if isinstance(columns, unicode):
        # PostgreSQL 9.1 stores JSONField as unicode
        columns = json.loads(columns)

    return JsonResponse({
        'columns': columns,
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
    if isinstance(columns, unicode):
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


def _mapping_suggestions(import_file_id, org_id, user):
    """
    Temp function for allowing both api version for mapping suggestions to
    return the same data. Move this to the mapping_suggestions once we can
    deprecate the old get_column_mapping_suggestion method.

    :param import_file_id: import file id
    :param org_id: organization id of user
    :param user: user object from request
    :return: dict
    """
    result = {'status': 'success'}

    membership = OrganizationUser.objects.select_related('organization') \
        .get(organization_id=org_id, user=user)
    organization = membership.organization

    import_file = ImportFile.objects.get(
        pk=import_file_id,
        import_record__super_organization_id=organization.pk
    )

    # Get a list of the database fields in a list
    md = mapping_data.MappingData()

    # TODO: Move this to the MappingData class and remove calling add_extra_data
    # Check if there are any DB columns that are not defined in the
    # list of mapping data.
    # NL 12/2/2016: Removed 'organization__isnull' Query because we only want the
    # the ones belonging to the organization
    columns = list(Column.objects.select_related('unit').filter(
        mapped_mappings__super_organization_id=org_id).exclude(column_name__in=md.keys))
    md.add_extra_data(columns)

    # Portfolio manager files have their own mapping scheme - yuck, really?
    if import_file.from_portfolio_manager:
        _log.debug("map Portfolio Manager input file")
        suggested_mappings = simple_mapper.get_pm_mapping(import_file.first_row_columns,
                                                          resolve_duplicates=True)
    else:
        _log.debug("custom mapping of input file")
        # All other input types
        suggested_mappings = mapper.build_column_mapping(
            import_file.first_row_columns,
            md.keys_with_table_names,
            previous_mapping=get_column_mapping,
            map_args=[organization],
            thresh=80  # percentage match that we require. 80% is random value for now.
        )
        # replace None with empty string for column names and PropertyState for tables
        for m in suggested_mappings:
            table, field, conf = suggested_mappings[m]
            if field is None:
                suggested_mappings[m][1] = u''

    # Fix the table name, eventually move this to the build_column_mapping and build_pm_mapping
    for m in suggested_mappings:
        table, dest, conf = suggested_mappings[m]
        if not table:
            suggested_mappings[m][0] = 'PropertyState'

    result['suggested_column_mappings'] = suggested_mappings
    result['column_names'] = md.building_columns
    result['columns'] = md.data

    return result


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
    deleting_cache_key = get_prog_key(
        'delete_organization_inventory',
        org_id
    )
    tasks.delete_organization_inventory.delay(org_id, deleting_cache_key)
    return JsonResponse({
        'status': 'success',
        'progress': 0,
        'progress_key': deleting_cache_key
    })
