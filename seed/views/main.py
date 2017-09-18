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
import uuid

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.files.storage import DefaultStorage
from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.template.context import RequestContext
from rest_framework import status
from rest_framework.decorators import api_view

from seed import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.decorators import (
    ajax_request, get_prog_key, require_organization_id
)
from seed.lib.exporter import Exporter
from seed.lib.mappings import mapper as simple_mapper
from seed.lib.mappings import mapping_data
from seed.lib.mcm import mapper
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.models import (
    Column,
    ProjectBuilding,
    get_column_mapping,
)
from seed.utils.api import api_endpoint
from seed.utils.buildings import (
    get_columns as utils_get_columns,
)
from seed.utils.cache import get_cache, set_cache
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
    return render_to_response(
        'seed/jasmine_tests/AngularJSTests.html',
        locals(), context_instance=RequestContext(request),
    )


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

    return render_to_response(
        'seed/index.html',
        locals(), context_instance=RequestContext(request),
    )


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
        response = render_to_response(
            'seed/404.html', {},
            context_instance=RequestContext(request)
        )
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
        response = render_to_response(
            'seed/404.html', {},
            context_instance=RequestContext(request)
        )
        response.status_code = 500
        return response


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])
def export_buildings(request):
    """
    Begins a building export process.

    Payload::

        {
            "export_name": "My Export",
            "export_type": "csv",
            "selected_buildings": [1234,], (optional list of building ids)
            "selected_fields": optional list of fields to export
            "select_all_checkbox": True // optional, defaults to False
        }

    Returns::

        {
            "success": True,
            "status": "success",
            "export_id": export_id; see export_buildings_download,
            "total_buildings": count of buildings,
        }
    """
    body = request.data

    export_name = body.get('export_name')
    export_type = body.get('export_type')

    selected_fields = body.get('selected_fields', [])
    selected_building_ids = body.get('selected_buildings', [])

    params = search.parse_body(request)

    project_id = params['project_id']

    buildings_queryset = search.orchestrate_search_filter_sort(
        params=params,
        user=request.user,
        skip_sort=True,
    )

    if body.get('select_all_checkbox', False):
        selected_buildings = buildings_queryset
    else:
        selected_buildings = buildings_queryset.filter(
            pk__in=selected_building_ids
        )

    export_id = str(uuid.uuid4())

    # If we receive a project ID, we don't actually want to export buildings,
    # we want to export ProjectBuildings -- but the frontend does not know that,
    # so we change the fieldnames on the backend instead so the exporter can
    # resolve them correctly
    if project_id:
        export_model = 'seed.ProjectBuilding'

        # Grab the project buildings associated with the given project id and
        # buildings list
        selected_buildings = ProjectBuilding.objects.filter(
            project_id=project_id,
            building_snapshot__in=tuple(
                selected_buildings.values_list('pk', flat=True)
            ),  # NOQA
        )

        # Swap the requested fieldnames to reflect the new point of reference
        _selected_fields = []
        for field in selected_fields:
            components = field.split("__", 1)
            if (components[0] == 'project_building_snapshots' and len(components) > 1):
                _selected_fields.append(components[1])
            else:
                _selected_fields.append("building_snapshot__%s" % field)
        selected_fields = _selected_fields
    else:
        export_model = 'seed.BuildingSnapshot'

    building_ids = tuple(selected_buildings.values_list('pk', flat=True))
    progress_key = "export_buildings__%s" % export_id
    result = {
        'progress_key': progress_key,
        'status': 'not-started',
        'progress': 0,
        'buildings_processed': 0,
        'total_buildings': len(building_ids),
    }
    set_cache(progress_key, result['status'], result)

    tasks.export_buildings.delay(
        export_id,
        export_name,
        export_type,
        building_ids,
        export_model,
        selected_fields,
    )

    return JsonResponse({
        "success": True,
        "status": "success",
        'progress': 100,
        'progress_key': progress_key,
        "export_id": export_id,
        "total_buildings": len(building_ids),
    })


@api_endpoint
@ajax_request
@login_required
@api_view(['POST'])
def export_buildings_progress(request):
    """
    Returns current progress on building export process.

    Payload::

        {
            "export_id": export_id from export_buildings
        }

    Returns::

        {
            'success': True,
            'status': 'success or error',
            'message': 'error message, if any',
            'buildings_processed': number of buildings exported
        }
    """
    body = request.data
    export_id = body.get('export_id')
    progress_key = "export_buildings__%s" % export_id
    progress_data = get_cache(progress_key)

    percent_done = progress_data['progress']
    total_buildings = progress_data['total_buildings']

    return JsonResponse({
        "success": True,
        "status": "success",
        'total_buildings': progress_data['total_buildings'],
        "buildings_processed": (percent_done / 100) * total_buildings
    })


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


@require_organization_id
@ajax_request
@login_required
@has_perm('requires_viewer')
@api_view(['GET'])
def get_columns(request):
    """
    Returns a JSON list of columns a user can select as his/her default

    Requires the organization_id as a query parameter
    """
    all_fields = request.query_params.get('all_fields', '')
    all_fields = True if all_fields.lower() == 'true' else False
    return JsonResponse(utils_get_columns(request.query_params['organization_id'], all_fields))


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
@api_view(['POST'])
def progress(request):
    """
    Get the progress (percent complete) for a task.

    Payload::

        {
            'progress_key': The progress key from starting a background task
        }

    Returns::

        {
            'progress_key': The same progress key,
            'progress': Percent completion
        }
    """

    progress_key = request.data.get('progress_key')

    if get_cache(progress_key):
        return JsonResponse(get_cache(progress_key))
    else:
        return JsonResponse({
            'progress_key': progress_key,
            'progress': 0,
            'status': 'waiting'
        })


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

# DMcQ: Test for building reporting
# @require_organization_id
# @api_endpoint
# @ajax_request
# @login_required
# @has_perm('requires_member')
# def get_building_summary_report_data(request):
#     """
#     This method returns basic, high-level data about a set of buildings, filtered by organization ID.

#     It expects as parameters

#     :GET:

#     :param start_date: The starting date for the data series with the format  `YYYY-MM-DD`
#     :param end_date: The starting date for the data series with the format  `YYYY-MM-DD`

#     Returns::

#         {
#             "status": "success",
#             "summary_data":
#             {
#                 "num_buildings": "number of buildings returned from query",
#                 "avg_eui": "average EUI for returned buildings",
#                 "avg_energy_score": "average energy score for returned buildings"
#             }
#         }

#     Units for return values are as follows:

#     +-----------+---------------+
#     | property  | units         |
#     +===========+===============+
#     | avg_eui   | kBtu/ft2/yr   |
#     +-----------+---------------+

#     ---

#     parameters:
#         - name: organization_id
#           description: User's organization which should be used to filter building query results
#           required: true
#           type: string
#           paramType: query
#         - start_date:
#           description: The start date for the entire dataset.
#           required: true
#           type: string
#           paramType: query
#         - end_date:
#           description: The end date for the entire dataset.
#           required: true
#           type: string
#           paramType: query

#     type:
#         status:
#             required: true
#             type: string
#         summary_data:
#             required: true
#             type: object


#     status codes:
#         - code: 400
#           message: Bad request, only GET method is available
#         - code: 401
#           message: Not authenticated
#         - code: 403
#           message: Insufficient rights to call this procedure

#     """

#     # The following is just dummy data...

#     if request.method != 'GET':
#         return HttpResponseBadRequest("This view replies only to GET methods")

#     # Read in x and y vars requested by client
#     try:
#         orgs = [request.GET['organization_id']]  # How should we capture user orgs here?
#     except Exception as e:
#         msg = "Error while calling the API function get_scatter_data_series, missing parameter"
#         _log.error(msg)
#         _log.exception(str(e))
#         return HttpResponseBadRequest(msg)

#     num_buildings = BuildingSnapshot.objects.filter(
#         super_organization__in=orgs,
#         canonicalbuilding__active=True
#     ).count()

#     avg_eui = 123
#     avg_energy_score = 321

#     data = {
#         "num_buildings": num_buildings,
#         "avg_eui": avg_eui,
#         "avg_energy_score": avg_energy_score,
#     }

#     # Send back to client
#     return {
#         'status': 'success',
#         'summary_data': data
#     }


# def get_raw_report_data(from_date, end_date, orgs, x_var, y_var):
#     """ This method returns data used to generate graphing reports. It expects as parameters

#         :GET:

#         :param from_date: The starting date for the data series.  Date object.
#         :param end_date: The starting date for the data series with the format. Date object.
#         :param x_var: The variable name to be assigned to the "x" value in the returned data series.
#         :param y_var: The variable name to be assigned to the "y" value in the returned data series.
#         :param orgs: The organizations to be used when querying data.

#         The x and y variables should be column names in the BuildingSnapshot table.  In theory they could
#         be in the extra_data too and this works but is currently disabled.

#         Returns::

#             bldg_counts:  dict that looks like
#               {
#                   year_ending : {"buildings_with_data": set(canonical ids),
#                   "buildings": set(canonical ids)
#               }
#                             This is a collection of all year_ending dates and ids
#                             the canonical buildings that have data for that year
#                             and those that have files with that year_ending but no
#                             valid data point
#                             E.G.
#                             "bldg_counts"     (pending)
#                                 __len__    int: 8
#                                 2000-12-31 (140037191378512)    dict: {
#                                   'buildings_w_data': set([35897, 35898]),
#                                   'buildings': set([35897, 35898])
#                                }
#                                 2001-12-31 (140037292480784)    dict: {
#                                   'buildings_w_data': set([35897, 35898]),
#                                   'buildings': set([35897, 35898])
#                               }
#             data:   dict that looks like
#               {
#                  canonical_id : {
#                      year_ending : {
#                          'x': x_value, 'y': y_value',
#                          'release_date': release_date,
#                          'building_snapshot_id': building_snapshot_id
#                      }
#                  }
#              }
#                     This is the actual data for the building.  The top level key is
#                     the canonical_id then the next level is the year_ending and
#                     under that is the actual data.  NOTE:  If the year has files
#                     for a building but no valid data there will be an entry for
#                     that year but the x and y values will be None.

#                     E.G.
#                     "data"     (pending)
#                         __len__    int: 2
#                         35897 (28780560)    defaultdict: defaultdict(<type 'dict'>, {datetime.date(2001, 12, 31): {'y': 95.0, 'x': 88.0, 'release_date': datetime.datetime(2001, 12, 31, 0, 0), 'building_snapshot_id': 35854}, datetime.date(2004, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2004, 12, 31, 0, 0), 'building_snapshot_id': 35866}, datetime.date(2003, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2003, 12, 31, 0, 0), 'building_snapshot_id': 35860}, datetime.date(2009, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2009, 12, 31, 0, 0), 'building_snapshot_id': 35884}, datetime.date(2007, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2007, 12, 31, 0, 0), 'building_snapshot_id': 35878}, datetime.date(2000, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2000, 12, 31, 0, 0), 'building_snapshot_id': 35850}, datetime.date(2010, 12, 31): {'y': 111.0, 'x': 21.0, 'release_date': datetime.datetime(2011, 12, 31, 0, 0...  # NOQA
#                             __len__    int: 8
#                             2000-12-31 (140037191378512)    dict: {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2000, 12, 31, 0, 0), 'building_snapshot_id': 35850}  # NOQA
#                             2001-12-31 (140037292480784)    dict: {'y': 95.0, 'x': 88.0, 'release_date': datetime.datetime(2001, 12, 31, 0, 0), 'building_snapshot_id': 35854}  # NOQA

#         """

#     # year_ending in the BuildingSnapshot model is a DateField which
#     # corresponds to a python datetime.date not a datetime.datetime.  Ensure a
#     # conversion here
#     try:
#         from_date = from_date.date()
#     except:
#         pass

#     try:
#         end_date = end_date.date()
#     except:
#         pass

#     # First get all building records for the orginization in the date range
#     # Can't just look for those that are not null since one of the things that
#     # needs to get reported is how many for a given year do not have data
#     # (i.e. have a null value for either x_var or y_var
#     bldgs = BuildingSnapshot.objects.filter(
#         super_organization__in=orgs,
#         year_ending__gte=from_date,
#         year_ending__lte=end_date
#     )

#     # data will be a dict of canonical building id -> year ending -> building data
#     data = defaultdict(lambda: defaultdict(dict))

#     # get a unique list of canonical buildings
#     canonical_buildings = set(bldg.tip for bldg in bldgs)

#     # "deleted" buildings just get their canonicalbuilding field set to false
#     # filter them out here.  There may be a way to do this in one query with the above but I
#     # don't see it now.
#     canonical_buildings = BuildingSnapshot.objects.filter(
#         canonicalbuilding__active=True,
#         pk__in=[x.id for x in canonical_buildings]
#     )

#     # if the BuildingSnapshot has the attribute use that directly.
#     # in the future if it should search extra_data but extra_data is still not
#     # searchable directly then this can be adjusted by replacing the last None with
#     # obj.extra_data[attr] if hasattr(obj, "extra_data") and attr in obj.extra_data else None
#     def get_attr_f(obj, attr):
#         return getattr(obj, attr, None)

#     bldg_counts = {}

#     def process_snapshot(canonical_building_id, snapshot):
#         # The data is meaningless here aside if there is no valid year_ending value
#         # even though the query at the beginning specifies a date range since this is using the tree
#         # some other records without a year_ending may have snuck back in.  Ignore them here.
#         if not hasattr(snapshot, "year_ending") or not isinstance(snapshot.year_ending, datetime.date):
#             return
#         # if the snapshot is not in the date range then don't process it
#         if not(from_date <= snapshot.year_ending <= end_date):
#             return

#         year_ending_year = snapshot.year_ending

#         if year_ending_year not in bldg_counts:
#             bldg_counts[year_ending_year] = {"buildings": set(), "buildings_w_data": set()}
#         release_date = get_attr_f(snapshot, "release_date")

#         # if there is no release_date then we have no way of priotizing vs
#         # other records with the same year_ending.  Plus it is an indication of
#         # something wrong so just exit here
#         if not release_date:
#             return

#         bldg_counts[year_ending_year]["buildings"].add(canonical_building_id)

#         if (
#                 (year_ending_year not in data[canonical_building_id]) or
#                 (not data[canonical_building_id][year_ending_year]) or
#                 (data[canonical_building_id][year_ending_year]["release_date"] < release_date)
#         ):
#             bldg_x = get_attr_f(snapshot, x_var)
#             bldg_y = get_attr_f(snapshot, y_var)
#             # what does it mean for a building to "have data"?  I am assuming
#             # it must have values for both x and y fields.  Change "and" to
#             # "or" to make it either and "True" to return everything
#             if bldg_x and bldg_y:
#                 bldg_counts[year_ending_year]["buildings_w_data"].add(canonical_building_id)

#                 data[canonical_building_id][year_ending_year] = {
#                     "building_snapshot_id": snapshot.id,
#                     "x": bldg_x,
#                     "y": bldg_y,
#                     "release_date": release_date,
#                 }
#             else:
#                 try:
#                     bldg_counts[year_ending_year]["buildings_w_data"].remove(canonical_building_id)
#                 except:
#                     pass

#                 # if this more recent data point does not have both x and y
#                 # values then the data for the year ending is now invalid mark
#                 # that here by giving both 'x' and 'y' a value of None can't
#                 # just delete the year since we need to retain the
#                 # release_date.  If the most recent release_date for a given
#                 # year_ending is not value then that means that year is not
#                 # valid for the building

#                 data[canonical_building_id][year_ending_year] = {
#                     "building_snapshot_id": snapshot.id,
#                     "x": None,
#                     "y": None,
#                     "release_date": release_date,
#                 }

#     for canonical_building in canonical_buildings:
#         canonical_building_id = canonical_building.id

#         # we changed from only using the unmerged snapshots to only using the
#         # merged snapshots.
#         # So start at the current canonical building and work back
#         process_snapshot(canonical_building_id, canonical_building)

#         if canonical_building.parent_tree:
#             current_canonical_bldg = canonical_building

#             # progress up the the tree processing merged snapshots until there
#             # are not any more
#             while current_canonical_bldg:
#                 # unmerged_snapshots = bldg.parents.filter(parents__isnull = True)
#                 previous_canonical_bldg = current_canonical_bldg.parents.filter(
#                     parents__isnull=False,
#                 )

#                 if previous_canonical_bldg.count():
#                     current_canonical_bldg = previous_canonical_bldg[0]
#                     process_snapshot(canonical_building_id, current_canonical_bldg)
#                 else:
#                     # There are no parents who have non-null parents themselves
#                     # meaning the parent must be the first record imported and
#                     # therefore the first canonical building
#                     current_canonical_bldg = current_canonical_bldg.parents.filter(
#                         parents__isnull=True,
#                     )
#                     # hopefully the record is always in index 1.  Otherwise I'm
#                     # not sure how to pick the right one.
#                     current_canonical_bldg = current_canonical_bldg.all()[1]
#                     process_snapshot(canonical_building_id, current_canonical_bldg)
#                     current_canonical_bldg = None

#     return bldg_counts, data


# @api_endpoint
# @ajax_request
# @login_required
# @has_perm('requires_member')
# def get_building_report_data(request):
#     """ This method returns a set of x,y building data for graphing. It expects as parameters

#         :GET:

#         :param start_date: The starting date for the data series with the format  `YYYY-MM-DD`
#         :param end_date: The starting date for the data series with the format  `YYYY-MM-DD`
#         :param x_var: The variable name to be assigned to the "x" value in the returned data series  # NOQA
#         :param y_var: The variable name to be assigned to the "y" value in the returned data series  # NOQA
#         :param organization_id: The organization to be used when querying data.

#         The x_var values should be from the following set of variable names:

#             - site_eui
#             - source_eui
#             - site_eui_weather_normalized
#             - source_eui_weather_normalized
#             - energy_score

#         The y_var values should be from the following set of variable names:

#             - gross_floor_area
#             - use_description
#             - year_built

#         This method includes building record count information as part of the
#         result JSON in a property called "building_counts."

#         This property provides data on the total number of buildings available
#         in each 'year ending' group, as well as the subset of those buildings
#         that have actual data to graph. By sending these  values in the result
#         we allow the client to easily build a message like "200 of 250
#         buildings in this group have data."

#         Returns::

#             {
#                 "status": "success",
#                 "chart_data": [
#                     {
#                         "id" the id of the building,
#                         "yr_e": the year ending value for this data point
#                         "x": value for x var,
#                         "y": value for y var,
#                     },
#                     ...
#                 ],
#                 "building_counts": [
#                     {
#                         "yr_e": string for year ending
#                         "num_buildings": number of buildings in query results
#                         "num_buildings_w_data": number of buildings with valid data in query results
#                     },
#                     ...
#                 ]
#                 "num_buildings": total number of buildings in query results,
#                 "num_buildings_w_data": total number of buildings with valid data in the query results  # NOQA
#             }

#         ---

#         parameters:
#             - name: x_var
#               description: Name of column in building snapshot database to be used for "x" axis
#               required: true
#               type: string
#               paramType: query
#             - name: y_var
#               description: Name of column in building snapshot database to be used for "y" axis
#               required: true
#               type: string
#               paramType: query
#             - start_date:
#               description: The start date for the entire dataset.
#               required: true
#               type: string
#               paramType: query
#             - end_date:
#               description: The end date for the entire dataset.
#               required: true
#               type: string
#               paramType: query
#             - name: organization_id
#               description: User's organization which should be used to filter building query results
#               required: true
#               type: string
#               paramType: query
#             - name: aggregate
#               description: Aggregates data based on internal rules (given x and y var)
#               required: true
#               type: string
#               paramType: query

#         type:
#             status:
#                 required: true
#                 type: string
#             chart_data:
#                 required: true
#                 type: array
#             num_buildings:
#                 required: true
#                 type: string
#             num_buildings_w_data:
#                 required: true
#                 type: string

#         status codes:
#             - code: 400
#               message: Bad request, only GET method is available
#             - code: 401
#               message: Not authenticated
#             - code: 403
#               message: Insufficient rights to call this procedure
#         """
#     from dateutil.parser import parse

#     if request.method != 'GET':
#         return HttpResponseBadRequest('This view replies only to GET methods')

#     # Read in x and y vars requested by client
#     try:
#         x_var = request.GET['x_var']
#         y_var = request.GET['y_var']
#         orgs = [request.GET['organization_id']]  # How should we capture user orgs here?
#         from_date = request.GET['start_date']
#         end_date = request.GET['end_date']

#     except Exception as e:
#         msg = "Error while calling the API function get_building_report_data, missing parameter"
#         _log.error(msg)
#         _log.exception(str(e))
#         return HttpResponseBadRequest(msg)

#     valid_values = [
#         'site_eui', 'source_eui', 'site_eui_weather_normalized',
#         'source_eui_weather_normalized', 'energy_score',
#         'gross_floor_area', 'use_description', 'year_built'
#     ]

#     if x_var not in valid_values or y_var not in valid_values:
#         return HttpResponseBadRequest('Invalid fields specified.')

#     try:
#         from_date = parse(from_date).date()
#         end_date = parse(end_date).date()
#     except Exception as e:
#         msg = "Couldn't convert date strings to date objects"
#         _log.error(msg)
#         _log.exception(str(e))
#         return HttpResponseBadRequest(msg)

#     bldg_counts, data = get_raw_report_data(from_date, end_date, orgs, x_var, y_var)
#     # now we have data as nested dictionaries like:
#     #
#     # canonical_building_id -> year_ending -> {building_snapshot_id, address_line_1, x, y}
#     # but the comment at the beginning o says to do it like a list of dicts
#     # that looks like
#     #                  "chart_data": [
#     #                  {
#     #                      "id" the id of the building,
#     #                      "yr_e": the year ending value for this data point
#     #                      "x": value for x var,
#     #                      "y": value for y var,
#     #                  },
#     #                  ...
#     #              ],

#     chart_data = []
#     building_counts = []
#     for year_ending, values in bldg_counts.items():
#         buildingCountItem = {
#             "num_buildings": len(values["buildings"]),
#             "num_buildings_w_data": len(values["buildings_w_data"]),
#             "yr_e": year_ending.strftime('%Y-%m-%d')
#         }
#         building_counts.append(buildingCountItem)

#     for canonical_id, year_ending_to_data_map in data.iteritems():
#         for year_ending, requested_data in year_ending_to_data_map.iteritems():
#             d = requested_data
#             # The point must have both an x and a y value or else it is not valid
#             if not (d["x"] and d["y"]):
#                 continue
#             d["id"] = canonical_id
#             d["yr_e"] = year_ending.strftime('%Y-%m-%d')
#             chart_data.append(d)

#     # Send back to client
#     return {
#         'status': 'success',
#         'chart_data': chart_data,
#         'building_counts': building_counts
#     }


# @api_endpoint
# @ajax_request
# @login_required
# @has_perm('requires_member')
# def get_aggregated_building_report_data(request):
#     """ This method returns a set of aggregated building data for graphing. It expects as parameters

#         :GET:

#         :param start_date: The starting date for the data series with the format  `YYYY-MM-DDThh:mm:ss+hhmm`
#         :param end_date: The starting date for the data series with the format  `YYYY-MM-DDThh:mm:ss+hhmm`
#         :param x_var: The variable name to be assigned to the "x" value in the returned data series
#         :param y_var: The variable name to be assigned to the "y" value in the returned data series
#         :param organization_id: The organization to be used when querying data.

#         The x_var values should be from the following set of variable names:

#             - site_eui
#             - source_eui
#             - site_eui_weather_normalized
#             - source_eui_weather_normalized
#             - energy_score

#         The y_var values should be from the following set of variable names:

#             - gross_floor_area
#             - use_description
#             - year_built

#         This method includes building record count information as part of the
#         result JSON in a property called "building_counts."

#         This property provides data on the total number of buildings available
#         in each 'year ending' group, as well as the subset of those buildings
#         that have actual data to graph. By sending these  values in the result
#         we allow the client to easily build a message like "200 of 250
#         buildings in this group have data."


#         Returns::

#             {
#                 "status": "success",
#                 "chart_data": [
#                     {
#                         "yr_e": x - group by year ending
#                         "x": x, - median value in group
#                         "y": y - average value thing
#                     },
#                     {
#                         "yr_e": x
#                         "x": x,
#                         "y": y
#                     }
#                     ...
#                 ],
#                 "building_counts": [
#                     {
#                         "yr_e": string for year ending - group by
#                         "num_buildings": number of buildings in query results
#                         "num_buildings_w_data": number of buildings with valid data in this group, BOTH x and y?  # NOQA
#                     },
#                     ...
#                 ]
#                 "num_buildings": total number of buildings in query results,
#                 "num_buildings_w_data": total number of buildings with valid data in query results
#             }

#         ---

#         parameters:
#             - name: x_var
#               description: Name of column in building snapshot database to be used for "x" axis
#               required: true
#               type: string
#               paramType: query
#             - name: y_var
#               description: Name of column in building snapshot database to be used for "y" axis
#               required: true
#               type: string
#               paramType: query
#             - start_date:
#               description: The start date for the entire dataset.
#               required: true
#               type: string
#               paramType: query
#             - end_date:
#               description: The end date for the entire dataset.
#               required: true
#               type: string
#               paramType: query
#             - name: organization_id
#               description: User's organization which should be used to filter building query results
#               required: true
#               type: string
#               paramType: query

#         type:
#             status:
#                 required: true
#                 type: string
#             chart_data:
#                 required: true
#                 type: array
#             building_counts:
#                 required: true
#                 type: array
#             num_buildings:
#                 required: true
#                 type: string
#             num_buildings_w_data:
#                 required: true
#                 type: string

#         status code:
#             - code: 400
#               message: Bad request, only GET method is available
#             - code: 401
#               message: Not authenticated
#             - code: 403
#               message: Insufficient rights to call this procedure


#         """

#     if request.method != 'GET':
#         return HttpResponseBadRequest('This view replies only to GET methods')

#     # Read in x and y vars requested by client
#     try:
#         x_var = request.GET['x_var']
#         y_var = request.GET['y_var']
#         orgs = [request.GET['organization_id']]  # How should we capture user orgs here?
#         from_date = request.GET['start_date']
#         end_date = request.GET['end_date']
#     except KeyError as e:
#         msg = "Error while calling the API function get_aggregated_building_report_data, missing parameter"  # NOQA
#         _log.error(msg)
#         _log.exception(str(e))
#         return HttpResponseBadRequest(msg)

#     valid_x_var_values = [
#         'site_eui', 'source_eui', 'site_eui_weather_normalized',
#         'source_eui_weather_normalized', 'energy_score'
#     ]

#     valid_y_var_values = [
#         'gross_floor_area', 'use_description', 'year_built'
#     ]

#     if x_var not in valid_x_var_values or y_var not in valid_y_var_values:
#         return HttpResponseBadRequest('Invalid fields specified.')

#     dt_from = None
#     dt_to = None
#     try:
#         dt_from = parse(from_date)
#         dt_to = parse(end_date)
#     except Exception as e:
#         msg = "Couldn't convert date strings to date objects"
#         _log.error(msg)
#         _log.exception(str(e))
#         return HttpResponseBadRequest(msg)

#     _, data = get_raw_report_data(dt_from, dt_to, orgs, x_var, y_var)

#     # Grab building snapshot ids from get_raw_report_data payload.
#     snapshot_ids = []
#     for k, v in data.items():
#         for date, building in v.items():
#             snapshot_ids.append(building['building_snapshot_id'])

#     bldgs = BuildingSnapshot.objects.filter(pk__in=snapshot_ids)

#     grouped_buildings = defaultdict(list)
#     for building in bldgs:
#         grouped_buildings[building.year_ending].append(building)

#     chart_data = []
#     building_counts = []
#     for year_ending, buildings in grouped_buildings.items():
#         yr_e = year_ending.strftime('%b %d, %Y')  # Dec 31, 2011

#         # Begin filling out building_counts object.

#         building_count_item = {
#             'yr_e': yr_e,
#             'num_buildings': len(buildings),
#             'num_buildings_w_data': 0
#         }

#         # Tally which buildings have both fields set.
#         for b in buildings:
#             if getattr(b, x_var) and getattr(b, y_var):
#                 building_count_item['num_buildings_w_data'] += 1

#         building_counts.append(building_count_item)

#         # End of building_counts object creation, begin filling out chart_data object.

#         if y_var == 'use_description':

#             # Group buildings in this year_ending group into uses
#             grouped_uses = defaultdict(list)
#             for b in buildings:
#                 if not getattr(b, y_var):
#                     continue
#                 grouped_uses[str(getattr(b, y_var)).lower()].append(b)

#             # Now iterate over use groups to make each chart item
#             for use, buildings_in_uses in grouped_uses.items():
#                 chart_data.append({
#                     'yr_e': yr_e,
#                     'x': median([
#                         getattr(b, x_var)
#                         for b in buildings_in_uses if getattr(b, x_var)
#                     ]),
#                     'y': use.capitalize()
#                 })

#         elif y_var == 'year_built':

#             # Group buildings in this year_ending group into decades
#             grouped_decades = defaultdict(list)
#             for b in buildings:
#                 if not getattr(b, y_var):
#                     continue
#                 grouped_decades['%s0' % str(getattr(b, y_var))[:-1]].append(b)

#             # Now iterate over decade groups to make each chart item
#             for decade, buildings_in_decade in grouped_decades.items():
#                 chart_data.append({
#                     'yr_e': yr_e,
#                     'x': median([
#                         getattr(b, x_var)
#                         for b in buildings_in_decade if getattr(b, x_var)
#                     ]),
#                     'y': '%s-%s' % (decade, '%s9' % str(decade)[:-1])  # 1990-1999
#                 })

#         elif y_var == 'gross_floor_area':
#             y_display_map = {
#                 0: '0-99k',
#                 100000: '100-199k',
#                 200000: '200k-299k',
#                 300000: '300k-399k',
#                 400000: '400-499k',
#                 500000: '500-599k',
#                 600000: '600-699k',
#                 700000: '700-799k',
#                 800000: '800-899k',
#                 900000: '900-999k',
#                 1000000: 'over 1,000k',
#             }
#             max_bin = max(y_display_map.keys())

#             # Group buildings in this year_ending group into ranges
#             grouped_ranges = defaultdict(list)
#             for b in buildings:
#                 if not getattr(b, y_var):
#                     continue
#                 area = getattr(b, y_var)
#                 # make sure anything greater than the biggest bin gets put in
#                 # the biggest bin
#                 range_bin = min(max_bin, round_down_hundred_thousand(area))
#                 grouped_ranges[range_bin].append(b)

#             # Now iterate over range groups to make each chart item
#             for range_floor, buildings_in_range in grouped_ranges.items():
#                 chart_data.append({
#                     'yr_e': yr_e,
#                     'x': median([
#                         getattr(b, x_var)
#                         for b in buildings_in_range if getattr(b, x_var)
#                     ]),
#                     'y': y_display_map[range_floor]
#                 })

#     # Send back to client
#     return {
#         'status': 'success',
#         'chart_data': chart_data,
#         'building_counts': building_counts
#     }
