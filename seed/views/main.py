"""
:copyright: (c) 2014 Building Energy Inc
"""

import json
import logging
import datetime
import os
import uuid

from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.core.files.storage import DefaultStorage
from django.db.models import Q
from annoying.decorators import render_to, ajax_request
from seed.lib.mcm import mapper
from seed.audit_logs.models import AuditLog
from seed.data_importer.models import ImportFile, ImportRecord, ROW_DELIMITER
from seed.tasks import (
    map_data,
    remap_data,
    match_buildings,
    save_raw_data as task_save_raw,
)
from seed.lib.superperms.orgs.decorators import has_perm
from seed import models, tasks
from seed.models import (
    get_column_mapping,
    save_snapshot_match,
    BuildingSnapshot,
    Column,
    ColumnMapping,
    Project,
    ProjectBuilding,
    get_ancestors,
    unmatch_snapshot_tree as unmatch_snapshot,
    CanonicalBuilding,
    ASSESSED_BS,
    PORTFOLIO_BS,
    GREEN_BUTTON_BS,
)
from seed.views.accounts import _get_js_role
from seed.lib.superperms.orgs.models import Organization, OrganizationUser, ROLE_MEMBER
from seed.utils.buildings import (
    get_columns as utils_get_columns,
    get_search_query,
    get_buildings_for_user_count
)
from seed.utils.api import api_endpoint
from seed.utils.generic import median, round_down_hundred_thousand
from seed.utils.projects import (
    get_projects, update_buildings_with_labels
)
from seed.utils.time import convert_to_js_timestamp
from seed.utils.mapping import get_mappable_types, get_mappable_columns
from .. import search
from seed.lib.exporter import Exporter
from seed.common import mapper as simple_mapper
from seed.common import views as vutil
from django.http import HttpResponseBadRequest

from dateutil.parser import parse
from collections import defaultdict

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name',
    'address_line_1',
    'city',
    'state_province',
]

_log = logging.getLogger(__name__)


@render_to('seed/jasmine_tests/AngularJSTests.html')
def angular_js_tests(request):
    """Jasmine JS unit test code covering AngularJS unit tests and ran
       by ./manage.py harvest

    """
    return locals()


def _get_default_org(user):
    """Gets the default org for a user and returns the id, name, and
    role_level. If no default organization is set for the user, the first
    organization the user has access to is set as default if it exists.

    :param user: the user to get the default org
    :returns: tuple (Organization id, Organization name, OrganizationUser role)
    """
    org = user.default_organization
    # check if user is still in the org, i.e. s/he wasn't removed from his/her
    # default org or didn't have a set org and try to set the first one
    if (not org
        or not OrganizationUser.objects.filter(organization=org, user=user).exists()
        ):
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


@render_to('seed/index.html')
@login_required
def home(request):
    """the main view for the app
        Sets in the context for the django template:
            app_urls: a json object of all the urls that is loaded in the JS
                      global namespace
            username: the request user's username (first and last name)
            AWS_UPLOAD_BUCKET_NAME: S3 direct upload bucket
            AWS_CLIENT_ACCESS_KEY: S3 direct upload client key
            FILE_UPLOAD_DESTINATION:  'S3' or 'filesystem'
    """
    username = request.user.first_name + " " + request.user.last_name
    if 's3boto' in settings.DEFAULT_FILE_STORAGE.lower():
        FILE_UPLOAD_DESTINATION = 'S3'
        AWS_UPLOAD_BUCKET_NAME = settings.AWS_BUCKET_NAME
        AWS_CLIENT_ACCESS_KEY = settings.AWS_UPLOAD_CLIENT_KEY
    elif 'FileSystemStorage' in settings.DEFAULT_FILE_STORAGE:
        FILE_UPLOAD_DESTINATION = 'filesystem'
    else:
        msg = "Only S3 and FileSystemStorage backends are supported"
        raise ImproperlyConfigured(msg)

    initial_org_id, initial_org_name, initial_org_user_role = _get_default_org(
        request.user
    )

    return locals()


@api_endpoint
@ajax_request
@login_required
def create_pm_mapping(request):
    """Create a mapping for PortfolioManager input columns.

    Payload::

        {
            columns: [ "name1", "name2", ... , "nameN"],
        }

    Returns::

        {
            success: true,
            mapping: [
                ["name1", "mapped1", {bedes: true|false, numeric: true|false}],
                ["name2", "mapped2", {bedes: true|false, numeric: true|false}],
                ...
                ["nameN", "mappedN", {bedes: true|false, numeric: true|false}]
            ]
        }
        -- OR --
        {
            success: false,
            reason: "message goes here"
        }
    """
    _log.info("create_pm_mapping: request.body='{}'".format(request.body))
    body = json.loads(request.body)

    # validate inputs
    invalid = vutil.missing_request_keys(['columns'], body)
    if invalid:
        return vutil.api_error(invalid)

    try:
        result = simple_mapper.get_pm_mapping('1.0', body['columns'])
    except ValueError as err:
        return vutil.api_error(str(err))
    json_result = [[c] + v.as_json() for c, v in result.items()]
    return vutil.api_success(mapping=json_result)


@api_endpoint
@ajax_request
@login_required
def export_buildings(request):
    """
    Begins a building export process.

    Payload::

        {
          "export_name": "My Export",
          "export_type": "csv",
          "selected_building": [1234,], (optional list of building ids)
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
    body = json.loads(request.body)

    export_name = body.get('export_name')
    export_type = body.get('export_type')

    building_ids = body.get('building_ids')

    selected_fields = body.get('selected_fields', [])

    selected_building_ids = body.get('selected_buildings', [])

    project_id = body.get('project_id')

    if not body.get('select_all_checkbox', False):
        selected_buildings = get_search_query(request.user, {})
        selected_buildings = selected_buildings.filter(
            pk__in=selected_building_ids
        )
    else:
        selected_buildings = get_search_query(request.user, body)
        selected_buildings = selected_buildings.exclude(
            pk__in=selected_building_ids
        )

    export_id = str(uuid.uuid4())

    # If we receive a project ID, we don't actually want to export buildings,
    # we want to export ProjectBuildings -- but the frontend doesn't know that,
    # so we change the fieldnames on the backend instead so the exporter can
    # resolve them correctly
    if project_id:
        export_model = 'seed.ProjectBuilding'

        # Grab the project buildings associated with the given project id and
        # buildings list
        selected_building_ids = [
            x[0] for x in selected_buildings.values_list('pk')
            ]
        selected_buildings = ProjectBuilding.objects.filter(
            project_id=project_id,
            building_snapshot__in=selected_building_ids)

        # Swap the requested fieldnames to reflect the new point of reference
        _selected_fields = []
        for field in selected_fields:
            components = field.split("__", 1)
            if (components[0] == 'project_building_snapshots'
                and len(components) > 1):
                _selected_fields.append(components[1])
            else:
                _selected_fields.append("building_snapshot__%s" % field)
        selected_fields = _selected_fields
    else:
        export_model = 'seed.BuildingSnapshot'

    building_ids = [x[0] for x in selected_buildings.values_list('pk')]

    # TODO: move the cache to the Exporter class
    cache.set("export_buildings__%s" % export_id, 0)

    tasks.export_buildings.delay(export_id, export_name, export_type, building_ids, export_model, selected_fields)

    return {
        "success": True,
        "status": "success",
        "export_id": export_id,
        "total_buildings": selected_buildings.count(),
    }


@api_endpoint
@ajax_request
@login_required
def export_buildings_progress(request):
    """
    Returns current progress on building export process.

    Payload::

        {"export_id": export_id from export_buildings }

    Returns::

        {'success': True,
         'status': 'success or error',
         'message': 'error message, if any',
         'buildings_processed': number of buildings exported
        }
    """
    body = json.loads(request.body)
    export_id = body.get('export_id')
    return {
        "success": True,
        "status": "success",
        "buildings_processed": cache.get("export_buildings__%s" % export_id),
    }


@api_endpoint
@ajax_request
@login_required
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
    body = json.loads(request.body)
    export_id = body.get('export_id')

    # This is non-ideal, it is returning the directory/s3 key and assumes that only one file lives in that
    # directory. This should really just return the file to be downloaded. Not sure we are doing multiple downloads at
    # the moment.
    export_subdir = Exporter.subdirectory_from_export_id(export_id)

    if 'FileSystemStorage' in settings.DEFAULT_FILE_STORAGE:
        file_storage = DefaultStorage()
        files = file_storage.listdir(export_subdir)

        if not files:
            return {
                'success': False,
                'status': 'error'
            }
        else:
            # get the first file in the directory -- which is the first entry of the second part of the tuple
            file_name = os.path.join(export_subdir, files[1][0])

            if file_storage.exists(file_name):
                url = file_storage.url(file_name)
                return {
                    'success': True,
                    "status": "success",
                    "url": url
                }
            else:
                return {
                    'success': False,
                    'message': 'Could not find file on server',
                    'status': 'error'
                }

    else:
        keys = list(DefaultStorage().bucket.list(export_subdir))

        if not keys or len(keys) > 1:
            return {
                "success": False,
                "status": "error",
            }

        download_key = keys[0]
        download_url = download_key.generate_url(900)

        return {
            'success': True,
            "status": "success",
            "url": download_url
        }


@ajax_request
@login_required
def get_total_number_of_buildings_for_user(request):
    """gets a count of all buildings in the user's organaztions"""
    buildings_count = get_buildings_for_user_count(request.user)

    return {'status': 'success', 'buildings_count': buildings_count}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_building(request):
    """
    Retrieves a building. If user doesn't belong to the building's org,
    fields will be masked to only those shared within the parent org's
    structure.

    :GET: Expects building_id and organization_id in query string.
    building_id should be the `caninical_building` ID for the building, not the
    BuildingSnapshot id.

    Returns::

        {
             'status': 'success or error',
             'message': 'error message, if any',
             'building': {'id': the building's id,
                          'canonical_building': the canonical building ID,
                          other fields this user has access to...
             },
             'imported_buildings': [ A list of buildings imported to create
                                     this building's record, in the same
                                     format as 'building'
                                   ],
             'projects': [
                // A list of the building's projects
                {
                    "building": {
                        "approved_date":07/30/2014,
                        "compliant": null,
                        "approver": "demo@buildingenergy.com"
                        "approved_date": "07/30/2014"
                        "compliant": null
                        "label": {
                            "color": "red",
                            "name": "non compliant",
                            id: 1
                        }
                    }
                    "description": null
                    "id": 3
                    "is_compliance": false
                    "last_modified_by_id": 1
                    "name": "project 1"
                    "owner_id": 1
                    "slug": "project-1"
                    "status": 1
                    "super_organization_id": 1
                },
                . . .
            ],
             'user_role': role of user in this org,
             'user_org_id': the org id this user belongs to
        }

    """
    building_id = request.GET.get('building_id')
    organization_id = request.GET.get('organization_id')
    org = Organization.objects.get(pk=organization_id)
    canon = CanonicalBuilding.objects.get(pk=building_id)
    building = canon.canonical_snapshot
    user_orgs = request.user.orgs.all()
    parent_org = user_orgs[0].get_parent()

    if (building.super_organization in user_orgs or parent_org in user_orgs):
        exportable_field_names = None  # show all
    else:
        # User isn't in the parent org or the building's org,
        # so only show shared fields.
        exportable_fields = parent_org.exportable_fields
        exportable_field_names = exportable_fields.values_list('name',
                                                               flat=True)

    building_dict = building.to_dict(exportable_field_names)

    ancestors = get_ancestors(building)

    # Add child node (in case it hasn't yet been matched with any other
    # buildings). When this happens, ancestors should also be the empty list.
    if building.source_type in [ASSESSED_BS, PORTFOLIO_BS, GREEN_BUTTON_BS]:
        ancestors.append(building)
    imported_buildings_list = []
    for b in ancestors:
        d = b.to_dict(exportable_field_names)
        # get deleted import file names without throwing an error
        imp_file = ImportFile.raw_objects.get(pk=b.import_file_id)
        d['import_file_name'] = imp_file.filename_only
        # do not show deleted import file sources
        if not imp_file.deleted:
            imported_buildings_list.append(d)
    imported_buildings_list.sort(key=lambda x: x['source_type'])

    projects = get_projects(building, org)
    ou = request.user.organizationuser_set.filter(
        organization=building.super_organization
    ).first()

    return {
        'status': 'success',
        'building': building_dict,
        'imported_buildings': imported_buildings_list,
        'projects': projects,
        'user_role': _get_js_role(ou.role_level) if ou else "",
        'user_org_id': ou.organization.pk if ou else "",
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_datasets_count(request):
    """
    Retrieves the number of datasets for an org.

    :GET: Expects organization_id in the query string.

    Returns::

        {'status': 'success',
         'datasets_count': Number of datasets belonging to this org.
        }

    """
    organization_id = request.GET.get('organization_id', '')
    datasets_count = Organization.objects.get(
        pk=organization_id).import_records.all().distinct().count()

    return {'status': 'success', 'datasets_count': datasets_count}


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
    return {
        'status': 'success',
        'buildings': search_results,
        'number_matching_search': building_count,
        'number_returned': len(search_results)
    }


@api_endpoint
@ajax_request
@login_required
def search_buildings(request):
    """
    Retrieves a paginated list of CanonicalBuildings matching search params.

    Payload::

        {
         'q': a string to search on (optional),
         'show_shared_buildings': True to include buildings from other
             orgs in this user's org tree,
         'order_by': which field to order by (e.g. pm_property_id),
         'import_file_id': ID of an import to limit search to,
         'filter_params': { a hash of Django-like filter parameters to limit
             query.  See seed.search.filter_other_params.  If 'project__slug'
             is included and set to a project's slug, buildings will include
             associated labels for that project.
           }
         'page': Which page of results to retrieve (default: 1),
         'number_per_page': Number of buildings to retrieve per page
                            (default: 10),
        }

    Returns::

        {
         'status': 'success',
         'buildings': [
          { all fields for buildings the request user has access to;
            e.g.:
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
    other_search_params = params['other_search_params']
    # add some filters to the dict of known column names so search_buildings
    # doesn't think they are part of extra_data
    db_columns, extra_data_sort, params['order_by'] = search.build_json_params(
        params['order_by'], params['sort_reverse']
    )

    # get all buildings for a user's orgs and sibling orgs
    orgs = request.user.orgs.all()
    whitelist_orgs = orgs
    other_orgs = []
    if params['show_shared_buildings']:
        other_orgs = search.build_shared_buildings_orgs(orgs)

    building_snapshots = search.create_building_queryset(
        orgs,
        params['exclude'],
        params['order_by'],
        other_orgs=other_orgs,
        extra_data_sort=extra_data_sort,
    )

    # full text search across a couple common fields
    buildings_queryset = search.search_buildings(
        params['q'], queryset=building_snapshots
    )
    buildings_queryset = search.filter_other_params(
        buildings_queryset, other_search_params, db_columns
    )
    # apply order_by here if extra_data_sort is True
    parent_org = orgs.first().parent_org
    below_threshold = False
    if (parent_org
        and parent_org.query_threshold
        and buildings_queryset.count() < parent_org.query_threshold
        ):
        below_threshold = True
    if extra_data_sort:
        ed_mapping = ColumnMapping.objects.filter(
            super_organization__in=orgs,
            column_mapped__column_name=params['order_by'],
        ).first()
        ed_column = ed_mapping.column_mapped.filter(
            column_name=params['order_by']
        ).first()
        ed_unit = ed_column.unit

        buildings_queryset = buildings_queryset.json_query(
            params['order_by'],
            order_by=params['order_by'],
            order_by_rev=params['sort_reverse'],
            unit=ed_unit,
        )
    buildings, building_count = search.generate_paginated_results(
        buildings_queryset,
        number_per_page=params['number_per_page'],
        page=params['page'],
        # Generally just orgs, sometimes all orgs with public fields.
        whitelist_orgs=whitelist_orgs,
        below_threshold=below_threshold,
    )
    project_slug = None
    if other_search_params and 'project__slug' in other_search_params:
        project_slug = other_search_params['project__slug']
    if params['project_id']:
        buildings = update_buildings_with_labels(
            buildings, params['project_id'])
    elif project_slug:
        project_id = Project.objects.get(slug=project_slug).pk
        buildings = update_buildings_with_labels(buildings, project_id)

    return {
        'status': 'success',
        'buildings': buildings,
        'number_matching_search': building_count,
        'number_returned': len(buildings)
    }


@api_endpoint
@ajax_request
@login_required
def search_building_snapshots(request):
    """
    Retrieves a paginated list of BuildingSnapshots matching search params.

    Payload::

        {
         'q': a string to search on (optional),
         'order_by': which field to order by (e.g. pm_property_id),
         'import_file_id': ID of an import to limit search to,
         'filter_params': { a hash of Django-like filter parameters to limit
             query.  See seed.search.filter_other_params.
           }
         'page': Which page of results to retrieve (default: 1),
         'number_per_page': Number of buildings to retrieve per page
                            (default: 10),
        }

    Returns::

        {
         'status': 'success',
         'buildings': [
          {
           'pm_property_id': ID of building (from Portfolio Manager),
           'address_line_1': First line of building's address,
           'property_name': Building's name, if any
           }...
          ]
         'number_matching_search': Total number of buildings matching search,
         'number_returned': Number of buildings returned for this page
        }
    """
    body = json.loads(request.body)
    q = body.get('q', '')
    other_search_params = body.get('filter_params', {})
    order_by = body.get('order_by', 'pm_property_id')
    if not order_by or order_by == '':
        order_by = 'pm_property_id'
    sort_reverse = body.get('sort_reverse', False)
    page = int(body.get('page', 1))
    number_per_page = int(body.get('number_per_page', 10))
    import_file_id = body.get(
        'import_file_id'
    ) or other_search_params.get('import_file_id')
    if sort_reverse:
        order_by = "-%s" % order_by

    # only search in ASSESED_BS, PORTFOLIO_BS, GREEN_BUTTON_BS
    building_snapshots = BuildingSnapshot.objects.order_by(order_by).filter(
        import_file__pk=import_file_id,
        source_type__in=[ASSESSED_BS, PORTFOLIO_BS, GREEN_BUTTON_BS],
    )

    fieldnames = [
        'pm_property_id',
        'address_line_1',
        'property_name',
    ]
    # add some filters to the dict of known column names so search_buildings
    # doesn't parse them as extra_data
    db_columns = get_mappable_types()
    db_columns['children__isnull'] = ''
    db_columns['project__slug'] = ''
    db_columns['import_file_id'] = ''

    buildings_queryset = search.search_buildings(
        q, fieldnames=fieldnames, queryset=building_snapshots
    )
    buildings_queryset = search.filter_other_params(
        buildings_queryset, other_search_params, db_columns
    )
    buildings, building_count = search.generate_paginated_results(
        buildings_queryset, number_per_page=number_per_page, page=page
    )

    return {
        'status': 'success',
        'buildings': buildings,
        'number_matching_search': building_count,
        'number_returned': len(buildings)
    }


@ajax_request
@login_required
def get_default_columns(request):
    """front end is expecting a JSON object with an array of field names
        i.e.
        {
            "columns": ["project_id", "name", "gross_floor_area"]
        }
    """
    columns = request.user.default_custom_columns

    if columns == '{}' or type(columns) == dict:
        initial_columns = True
        columns = DEFAULT_CUSTOM_COLUMNS
    else:
        initial_columns = False
    if type(columns) == unicode:
        # postgres 9.1 stores JSONField as unicode
        columns = json.loads(columns)

    return {
        'status': 'success',
        'columns': columns,
        'initial_columns': initial_columns,
    }


@ajax_request
@login_required
def set_default_columns(request):
    """sets the default value for the user's default_custom_columns"""
    body = json.loads(request.body)
    columns = body['columns']
    show_shared_buildings = body.get('show_shared_buildings')
    request.user.default_custom_columns = columns
    if show_shared_buildings is not None:
        request.user.show_shared_buildings = show_shared_buildings
    request.user.save()
    return {'status': 'success'}


@ajax_request
@login_required
@has_perm('requires_viewer')
def get_columns(request):
    """returns a JSON list of columns a user can select as his/her default

    :GET: Expects organization_id in the query string.
    """
    organization_id = request.GET.get('organization_id', '')
    is_project = request.GET.get('is_project', '')
    all_fields = request.GET.get('all_fields', '')
    is_project = True if is_project.lower() == 'true' else False
    all_fields = True if all_fields.lower() == 'true' else False
    return utils_get_columns(is_project, organization_id, all_fields)


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def save_match(request):
    """
    Adds or removes a match between two BuildingSnapshots.
    Creating a match creates a new BuildingSnapshot with merged data.

    Payload::

        {
         'organization_id': current user organization id,
         'source_building_id': ID of first BuildingSnapshot,
         'target_building_id': ID of second BuildingSnapshot,
         'create_match': True to create match, False to remove it,
         'organization_id': ID of user's organization
        }

    Returns::

        {
            'status': 'success',
            'child_id': The ID of the newly-created BuildingSnapshot
                        containing merged data from the two parents.
        }
    """
    body = json.loads(request.body)
    create = body.get('create_match')
    b1_pk = body['source_building_id']
    b2_pk = body.get('target_building_id')
    child_id = None

    # check some perms
    b1 = BuildingSnapshot.objects.get(pk=b1_pk)
    if create:
        b2 = BuildingSnapshot.objects.get(pk=b2_pk)
        if b1.super_organization_id != b2.super_organization_id:
            return {
                'status': 'error',
                'message': (
                    'Only buildings within an organization can be matched'
                )
            }
    if b1.super_organization_id != int(body.get('organization_id')):
        return {
            'status': 'error',
            'message': (
                'The source building does not belong to the organization'
            )
        }

    if create:
        child_id, changelist = save_snapshot_match(
            b1_pk, b2_pk, user=request.user, match_type=2, default_pk=b2_pk
        )
        child_id = child_id.pk
        cb = CanonicalBuilding.objects.get(buildingsnapshot__id=child_id)
        AuditLog.objects.log_action(
            request, cb, body['organization_id'],
            action_note='Matched building.'
        )
    else:
        cb = b1.canonical_building or b1.co_parent.canonical_building
        AuditLog.objects.log_action(
            request, cb, body['organization_id'],
            action_note='Unmatched building.'
        )
        unmatch_snapshot(b1_pk)
    resp = {
        'status': 'success',
        'child_id': child_id,
    }
    return resp


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_match_tree(request):
    """returns the BuildingSnapshot tree

    :GET: Expects organization_id and building_id in the query string

    Returns::

        {
            'status': 'success',
            'match_tree': [ // array of all the members of the tree
                {
                    "id": 333,
                    "coparent": 223,
                    "child": 443,
                    "parents": [],
                    "canonical_building_id": 1123
                },
                {
                    "id": 223,
                    "coparent": 333,
                    "child": 443,
                    "parents": [],
                    "canonical_building_id": 1124
                },
                {
                    "id": 443,
                    "coparent": null,
                    "child": 9933,
                    "parents": [333, 223],
                    "canonical_building_id": 1123
                },
                {
                    "id": 9933,
                    "coparent": null,
                    "child": null,
                    "parents": [443],
                    "canonical_building_id": 1123
                },
                ...
            ]
        }
    """
    building_id = request.GET.get('building_id', '')
    bs = BuildingSnapshot.objects.get(pk=building_id)
    # since our tree has the structure of two parents and one child, we can go
    # to the tip and look up, otherwise it's hard to keep track of the
    # co-parent trees of the children.
    tree = bs.tip.parent_tree + [bs.tip]
    tree = map(lambda b: b.to_dict(), tree)
    return {
        'status': 'success',
        'match_tree': tree,
    }


def _parent_tree_coparents(snapshot):
    """
    Takes a BuildingSnapshot inst. Climbs the snapshot tree upward and
    returns (root, parent_coparents,) where parent_coparents is every
    coparent on the path from the root to the snapshot's coparents and
    the root node. Does not return internal nodes from the path.

    currently, the order that the coparents are returned is not specified
    and should not be relied on.

    e.g. given this tree of snapshots

                C0       C1
                 |       |
                B0  B1   |
                 \  /   B3
                  B2   /
                   \  /
                    B4  B5
                     \  /
                      B6
                       |
                      B7  B8
                       \  /
                        B9
                         \ ...

    if called with B9 as the snapshot node (note that B9's
    canonical_building will be C0), then this will return:
    (
     B0, # root
     [B0, B1, B3, B5, B8] # parent_coparents
    )

    if called with B4, and B4.canonical_building is C0, this
    will return:
    (
     B0, # root
     [B0, B1, B3] # parent_coparents
    )

    if called with B4, and B4.canonical_building is C1, this
    will return:
    (
     B3, # root
     [B2, B3] # parent_coparents
    )

    if called with B5 (and B5 has no canonical_building), this
    will use B5's coparent's canonical_building and will return:
    (
     B0, # root
     [B0, B1, B3] # parent_coparents
    )

    """
    result_nodes = []
    root = snapshot
    canon = root.canonical_building

    if (not canon) and root.co_parent and root.co_parent.canonical_building:
        root = root.co_parent
        canon = root.canonical_building

    while root and not (root.parents.count() == 0):
        parents = root.parents.all()
        root = parents.filter(canonical_building=canon).first()
        coparents = parents.exclude(pk=root.pk)
        result_nodes = result_nodes + list(coparents)

    result_nodes.append(root)

    return (root, result_nodes,)


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_coparents(request):
    """
    Returns the nodes in the BuildingSnapshot tree that can be unmatched.


    :GET: Expects organization_id and building_id in the query string

    Returns::

        {
            'status': 'success',
            'coparents': [
                {
                    "id": 333,
                    "coparent": 223,
                    "child": 443,
                    "parents": [],
                    "canonical_building_id": 1123
                },
                {
                    "id": 223,
                    "coparent": 333,
                    "child": 443,
                    "parents": [],
                    "canonical_building_id": 1124
                },
                ...
            ]
        }
    """
    building_id = request.GET.get('building_id', '')
    node = BuildingSnapshot.objects.get(pk=building_id)

    # we need to climb up 'root's parents to find the other matched
    # snapshots
    root, proto_result = _parent_tree_coparents(node)

    if node.canonical_building and node.co_parent:
        proto_result.append(node.co_parent)
    elif node.co_parent and node.co_parent.canonical_building:
        proto_result.append(node)

    while node.children.first():
        child = node.children.first()
        if child.co_parent:
            proto_result.append(child.co_parent)
        node = child

    result = map(lambda b: b.to_dict(), proto_result)

    tip = root.tip
    tree = tip.parent_tree + [tip]
    tree = map(lambda b: b.to_dict(), tree)
    response = {
        'status': 'success',
        'coparents': result,
        'match_tree': tree,
        'tip': tip.to_dict(),
    }

    return response


@api_endpoint
@ajax_request
@login_required
def get_PM_filter_by_counts(request):
    """
    Retrieves the number of matched and unmatched BuildingSnapshots for
    a given ImportFile record.

    :GET: Expects import_file_id corresponding to the ImportFile in question.

    Returns::

        {'status': 'success',
         'matched': Number of BuildingSnapshot objects that have matches,
         'unmatched': Number of BuildingSnapshot objects with no matches.
        }
    """
    import_file_id = request.GET.get('import_file_id', '')

    matched = BuildingSnapshot.objects.filter(
        import_file__pk=import_file_id,
        source_type__in=[2, 3],
        children__isnull=False
    ).count()
    unmatched = BuildingSnapshot.objects.filter(
        import_file__pk=import_file_id,
        source_type__in=[2, 3],
        children__isnull=True,
        duplicate__isnull = True
    ).count()
    duplicates = BuildingSnapshot.objects.filter(
        import_file__pk=import_file_id,
        source_type__in=[2, 3],
        duplicate__isnull = False
    ).count()
    return {
        'status': 'success',
        'matched': matched,
        'unmatched': unmatched,
        'duplicates': duplicates,
    }

@api_endpoint
@ajax_request
@login_required
def delete_duplicates_from_import_file(request):
    """
    Retrieves the number of matched and unmatched BuildingSnapshots for
    a given ImportFile record.

    :GET: Expects import_file_id corresponding to the ImportFile in question.

    Returns::

        {'status': 'success',
         'deleted': Number of duplicates deleted
        }
    """
    import_file_id = request.GET.get('import_file_id', '')


    orig_duplicate_ct = BuildingSnapshot.objects.filter(
        import_file__pk=import_file_id,
        source_type__in=[2, 3],
        duplicate__isnull = False
    ).count()
    BuildingSnapshot.objects.filter(
        import_file__pk=import_file_id,
        source_type__in=[2, 3],
        duplicate__isnull = False
    ).delete()
    new_duplicate_ct = BuildingSnapshot.objects.filter(
        import_file__pk=import_file_id,
        source_type__in=[2, 3],
        duplicate__isnull = False
    ).count()
    return {
        'status': 'success',
        'deleted': orig_duplicate_ct - new_duplicate_ct,
    }


@api_endpoint
@ajax_request
@login_required
def get_column_mapping_suggestions(request):
    """
    Returns suggested mappings from an uploaded file's headers to known
    data fields.

    Payload::

        {'import_file_id': The ID of the ImportRecord to examine,
         'org_id': The ID of the user's organization}

    Returns::

        {'status': 'success',
         'suggested_column_mappings':
               {
                column header from file: [ (destination_column, score) ...]
                ...
               }
         'building_columns': [ a list of all possible columns ],
         'building_column_types': [a list of column types corresponding to
                                   building_columns],
             ]
        }
    """
    body = json.loads(request.body)
    import_file = ImportFile.objects.get(pk=body.get('import_file_id'))
    org_id = body.get('org_id')
    result = {'status': 'success'}
    # Make a dictionary of the column names and their respective types.
    # Build this dictionary from BEDES fields (the null organization columns,
    # and all of the column mappings that this organization has previously
    # saved.
    field_mappings = get_mappable_types()
    field_names = field_mappings.keys()
    column_types = {}

    # for c in Column.objects.filter(
    #     Q(mapped_mappings__super_organization=org_id) |
    #     Q(organization__isnull=True)
    # ).exclude(
    #     # mappings get created to mappable types
    #     # but we deal with them manually so don't
    #     # include them here
    #     column_name__in=field_names
    # ):

    # Note on exclude:
    # mappings get created to mappable types but we deal with them manually
    # so don't include them here
    columns = Column.objects.select_related('unit').prefetch_related('schemas') \
        .filter(Q(mapped_mappings__super_organization=org_id) | Q(organization__isnull=True)) \
        .exclude(column_name__in=field_names)

    for c in columns:
        if c.unit:
            unit = c.unit.get_unit_type_display()
        else:
            unit = 'string'
        if c.schemas.first():
            schema = c.schemas.first().name
        else:
            schema = ''
        column_types[c.column_name] = {
            'unit_type': unit.lower(),
            'schema': schema,
        }

    building_columns = sorted(column_types.keys())
    db_columns = sorted(field_names)
    building_columns = db_columns + building_columns

    db_columns = get_mappable_types()
    for k, v in db_columns.items():
        db_columns[k] = {
            'unit_type': v if v else 'string',
            'schema': 'BEDES',
        }
    column_types.update(db_columns)

    # Portfolio manager files have their own mapping scheme
    if import_file.from_portfolio_manager:
        _log.info("map Portfolio Manager input file")
        suggested_mappings = {}
        ver = import_file.source_program_version

        #if there is no pm mapping found but the file has already been matched
        #then effectively the mappings are already known with a confidence of 100
        no_pm_mappings_confience = 100 if import_file.matching_done else 0

        for col, item in simple_mapper.get_pm_mapping(
                ver, import_file.first_row_columns,
                include_none=True).items():
            if item is None:
                suggested_mappings[col] = (col, no_pm_mappings_confience)
            else:
                cleaned_field = item.field
                suggested_mappings[col] = (cleaned_field, 100)

    else:
        # All other input types
        suggested_mappings = mapper.build_column_mapping(
            import_file.first_row_columns,
            column_types.keys(),
            previous_mapping=get_column_mapping,
            map_args=[import_file.import_record.super_organization],
            thresh=20  # percentage match we require
        )
        # replace None with empty string for column names
        for m in suggested_mappings:
            dest, conf = suggested_mappings[m]
            if dest is None:
                suggested_mappings[m][0] = u''
    result['suggested_column_mappings'] = suggested_mappings
    result['building_columns'] = building_columns
    result['building_column_types'] = column_types

    return result


@api_endpoint
@ajax_request
@login_required
def get_raw_column_names(request):
    """
    Retrieves a list of all column names from an ImportFile.

    Payload::

        {'import_file_id': The ID of the ImportFile}

    Returns::

        {'status': 'success',
         'raw_columns': [
             list of strings of the header row of the ImportFile
             ]
        }
    """
    body = json.loads(request.body)
    import_file = ImportFile.objects.get(pk=body.get('import_file_id'))

    return {
        'status': 'success',
        'raw_columns': import_file.first_row_columns
    }


@api_endpoint
@ajax_request
@login_required
def get_first_five_rows(request):
    """
    Retrieves the first five rows of an ImportFile.

    Payload::

        {'import_file_id': The ID of the ImportFile}

    Returns::

        {'status': 'success',
         'first_five_rows': [
            [list of strings of header row],
            [list of strings of first data row],
            ...
            [list of strings of fourth data row]
         ]
        }
    """
    body = json.loads(request.body)
    import_file = ImportFile.objects.get(pk=body.get('import_file_id'))

    rows = [
        r.split(ROW_DELIMITER)
        for r in import_file.cached_second_to_fifth_row.splitlines()
        ]

    return {
        'status': 'success',
        'first_five_rows': [
            dict(
                zip(import_file.first_row_columns, row)
            ) for row in rows
            ]
    }


def _column_fields_to_columns(fields, organization):
    """Take a list of str, and turn it into a list of Column objects.

    :param fields: list of str. (optionally a single string).
    :param organization: superperms.Organization instance.
    :returns: list of Column instances.
    """
    if fields is None:
        return None

    col_fields = []  # Container for the strings of the column_names
    if isinstance(fields, list):
        col_fields.extend(fields)
    else:
        col_fields = [fields]

    cols = []  # Container for our Column instances.

    # It'd be nice if we could do this in a batch.
    for col_name in col_fields:
        if not col_name:
            continue

        col = None

        is_extra_data = col_name not in get_mappable_columns()
        org_col = Column.objects.filter(
            organization=organization,
            column_name=col_name,
            is_extra_data=is_extra_data
        ).first()

        if org_col is not None:
            col = org_col

        else:
            # Try for "global" column definitions, e.g. BEDES.
            global_col = Column.objects.filter(
                organization=None,
                column_name=col_name
            ).first()

            if global_col is not None:
                # create organization mapped column
                global_col.pk = None
                global_col.id = None
                global_col.organization = organization
                global_col.save()

                col = global_col

            else:
                col, _ = Column.objects.get_or_create(
                    organization=organization,
                    column_name=col_name,
                    is_extra_data=is_extra_data,
                )

        cols.append(col)

    return cols


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def save_column_mappings(request):
    """
    Saves the mappings between the raw headers of an ImportFile and the
    destination fields in the BuildingSnapshot model.

    Valid source_type values are found in ``seed.models.SEED_DATA_SOURCES``

    Payload::

        {
            "import_file_id": ID of the ImportFile record,
            "mappings": [
                ["destination_field": "raw_field"], #direct mapping
                ["destination_field2":
                    ["raw_field1", "raw_field2"], #concatenated mapping
                ...
            ]
        }

    Returns::

        {'status': 'success'}
    """
    body = json.loads(request.body)
    import_file = ImportFile.objects.get(pk=body.get('import_file_id'))
    organization = import_file.import_record.super_organization
    mappings = body.get('mappings', [])
    for mapping in mappings:
        dest_field, raw_field = mapping
        if dest_field == '':
            dest_field = None

        dest_cols = _column_fields_to_columns(dest_field, organization)
        raw_cols = _column_fields_to_columns(raw_field, organization)
        try:
            column_mapping, created = ColumnMapping.objects.get_or_create(
                super_organization=organization,
                column_raw__in=raw_cols,
            )
        except ColumnMapping.MultipleObjectsReturned:
            # handle the special edge-case where remove dupes doesn't get
            # called by ``get_or_create``
            ColumnMapping.objects.filter(
                super_organization=organization,
                column_raw__in=raw_cols,
            ).delete()
            column_mapping, created = ColumnMapping.objects.get_or_create(
                super_organization=organization,
                column_raw__in=raw_cols,
            )

        # Clear out the column_raw and column mapped relationships.
        column_mapping.column_raw.clear()
        column_mapping.column_mapped.clear()

        # Add all that we got back from the interface back in the M2M rel.
        [column_mapping.column_raw.add(raw_col) for raw_col in raw_cols]
        if dest_cols is not None:
            [
                column_mapping.column_mapped.add(dest_col)
                for dest_col in dest_cols
                ]

        column_mapping.user = request.user
        column_mapping.save()

    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
@has_perm('can_modify_data')
def create_dataset(request):
    """
    Creates a new empty dataset (ImportRecord).

    Payload::

        {
         "name": Name of new dataset, e.g. "2013 city compliance dataset"
         "organization_id": ID of the org this dataset belongs to
        }

    Returns::

        {'status': 'success',
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


@api_endpoint
@ajax_request
@login_required
def get_datasets(request):
    """
    Retrieves all datasets for the user's organization.

    :GET: Expects 'organization_id' of org to retrieve datasets from
        in query string.

    Returns::

        {'status': 'success',
         'datasets':  [
             {'name': Name of ImportRecord,
              'number_of_buildings': Total number of buildings in
                                     all ImportFiles,
              'id': ID of ImportRecord,
              'updated_at': Timestamp of when ImportRecord was last modified,
              'last_modified_by': Email address of user making last change,
              'importfiles': [
                  {'name': Name of associated ImportFile, e.g. 'buildings.csv',
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

    org = Organization.objects.get(pk=request.GET.get('organization_id'))
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
def get_dataset(request):
    """
    Retrieves ImportFile objects for one ImportRecord.

    :GET: Expects dataset_id for an ImportRecord in the query string.

    Returns::

        {'status': 'success',
         'dataset':
             {'name': Name of ImportRecord,
              'number_of_buildings': Total number of buildings in
                                     all ImportFiles for this dataset,
              'id': ID of ImportRecord,
              'updated_at': Timestamp of when ImportRecord was last modified,
              'last_modified_by': Email address of user making last change,
              'importfiles': [
                  {'name': Name of associated ImportFile, e.g. 'buildings.csv',
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
def get_import_file(request):
    """
    Retrieves details about an ImportFile.

    :GET: Expects import_file_id in the query string.

    Returns::

        {'status': 'success',
         'import_file': {
            "name": Name of the uploaded file,
            "number_of_buildings": number of buildings in the file,
            "number_of_mappings": number of mapped columns,
            "number_of_cleanings": number of cleaned fields,
            "source_type": type of data in file, e.g. 'Assessed Raw'
            "number_of_matchings": Number of matched buildings in file,
            "id": ImportFile ID,
            'dataset': {
                'name': Name of ImportRecord file belongs to,
                'id': ID of ImportRecord file belongs to,
                'importfiles': [  # All ImportFiles in this ImportRecord, with
                    # requested ImportFile first:
                    {'name': Name of file,
                     'id': ID of ImportFile
                    }
                    ...
                ]
            }
          }
        }
    """
    from seed.models import obj_to_dict

    import_file_id = request.GET.get('import_file_id', '')
    orgs = request.user.orgs.all()
    import_file = ImportFile.objects.get(
        pk=import_file_id
    )
    d = ImportRecord.objects.filter(
        super_organization__in=orgs, pk=import_file.import_record_id
    )
    # check if user has access to the import file
    if not d.exists():
        return {
            'status': 'success',
            'import_file': {},
        }

    f = obj_to_dict(import_file)
    f['name'] = import_file.filename_only
    f['dataset'] = obj_to_dict(import_file.import_record)
    # add the importfiles for the matching select
    f['dataset']['importfiles'] = []
    files = f['dataset']['importfiles']
    for i in import_file.import_record.files:
        files.append({
            'name': i.filename_only,
            'id': i.pk
        })
    # make the first element in the list the current import file
    i = files.index({
        'name': import_file.filename_only,
        'id': import_file.pk
    })
    files[0], files[i] = files[i], files[0]

    return {
        'status': 'success',
        'import_file': f,
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def delete_file(request):
    """
    Deletes an ImportFile from a dataset.

    Payload::
    {
        "file_id": ImportFile id,
        "organization_id": current user organization id
    }

    Returns::

        {'status': 'success' or 'error',
         'message': 'error message, if any'
        }
    """
    if request.method != 'DELETE':
        return {
            'status': 'error',
            'message': 'only HTTP DELETE allowed',
        }
    body = json.loads(request.body)
    file_id = body.get('file_id', '')
    import_file = ImportFile.objects.get(pk=file_id)
    d = ImportRecord.objects.filter(
        super_organization_id=body['organization_id'],
        pk=import_file.import_record.pk
    )
    # check if user has access to the dataset
    if not d.exists():
        return {
            'status': 'error',
            'message': 'user does not have permission to delete file',
        }

    import_file.delete()
    return {
        'status': 'success',
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def delete_dataset(request):
    """
    Deletes all files from a dataset and the dataset itself.

    :DELETE: Expects 'dataset_id' for an ImportRecord in the query string.

    Returns::

        {'status': 'success' or 'error',
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
def update_dataset(request):
    """
    Updates the name of a dataset.

    Payload::

        {'dataset':
            {'id': The ID of the Import Record,
             'name': The new name for the ImportRecord
            }
        }

    Returns::

        {'status': 'success' or 'error',
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
@has_perm('can_modify_data')
def save_raw_data(request):
    """
    Starts a background task to import raw data from an ImportFile
    into BuildingSnapshot objects.

    Payload::

        {'file_id': The ID of the ImportFile to be saved}

    Returns::

        {'status': 'success' or 'error',
         'progress_key': ID of background job, for retrieving job progress
        }
    """
    body = json.loads(request.body)
    import_file_id = body.get('file_id')
    if not import_file_id:
        return {'status': 'error'}

    return task_save_raw(import_file_id)


@api_endpoint
@ajax_request
@login_required
@has_perm('can_modify_data')
def start_mapping(request):
    """
    Starts a background task to convert imported raw data into
    BuildingSnapshots, using user's column mappings.

    Payload::

        {'file_id': The ID of the ImportFile to be mapped}

    Returns::

        {'status': 'success' or 'error',
         'progress_key': ID of background job, for retrieving job progress
        }
    """
    body = json.loads(request.body)
    import_file_id = body.get('file_id')
    if not import_file_id:
        return {'status': 'error'}

    return map_data(import_file_id)


@api_endpoint
@ajax_request
@login_required
@has_perm('can_modify_data')
def remap_buildings(request):
    """
    Re-run the background task to remap buildings as if it hadn't happened at
    all. Deletes mapped buildings for a given ImportRecord, resets status.

    NB: will not work if buildings have been merged into CanonicalBuilings.

    Payload::

        {'file_id': The ID of the ImportFile to be remapped}

    Returns::

        {'status': 'success' or 'error',
         'progress_key': ID of background job, for retrieving job progress
        }
    """
    body = json.loads(request.body)
    import_file_id = body.get('file_id')
    if not import_file_id:
        return {'status': 'error', 'message': 'Import File does not exist'}

    return remap_data(import_file_id)


@api_endpoint
@ajax_request
@login_required
@has_perm('can_modify_data')
def start_system_matching(request):
    """
    Starts a background task to attempt automatic matching between buildings
    in an ImportFile with other existing buildings within the same org.

    Payload::

        {'file_id': The ID of the ImportFile to be matched}

    Returns::

        {'status': 'success' or 'error',
         'progress_key': ID of background job, for retrieving job progress
        }
    """
    body = json.loads(request.body)
    import_file_id = body.get('file_id')
    if not import_file_id:
        return {'status': 'error'}

    return match_buildings(import_file_id, request.user.pk)


@api_endpoint
@ajax_request
@login_required
def progress(request):
    """
    Get the progress (percent complete) for a task.

    Payload::

        {'progress_key': The progress key from starting a background task}

    Returns::

        {'progress_key': The same progress key,
         'progress': Percent completion
        }
    """

    progress_key = json.loads(request.body).get('progress_key')

    if cache.get(progress_key):
        result = cache.get(progress_key)
        # The following if statement can be removed once all progress endpoints have been updated to the new json syntax
        if type(result) != dict:
            result = {'progress': result}
        result['progress_key'] = progress_key
        return result
    else:
        return {
            'progress_key': progress_key,
            'progress': 0,
            'status': 'waiting'
        }


@api_endpoint
@ajax_request
@login_required
@has_perm('can_modify_data')
def update_building(request):
    """
    Manually updates a building's record.  Creates a new BuildingSnapshot for
    the resulting changes.

    :PUT:

        {
        'organization_id': organization id,
        'building':
            {
            'canonical_building': The canonical building ID
            'fieldname': 'value'... The rest of the fields in the
                BuildingSnapshot; see get_columns() endpoint for complete
                list.
            }
        }

    Returns::

        {'status': 'success',
         'child_id': The ID of the newly-created BuildingSnapshot
        }
    """
    body = json.loads(request.body)
    # Will be a dict representation of a hydrated building, incl pk.
    building = body.get('building')
    org_id = body['organization_id']
    canon = CanonicalBuilding.objects.get(pk=building['canonical_building'])
    old_snapshot = canon.canonical_snapshot

    new_building = models.update_building(old_snapshot, building, request.user)

    resp = {'status': 'success',
            'child_id': new_building.pk}

    AuditLog.objects.log_action(request, canon, org_id, resp)
    return resp


@api_endpoint
@ajax_request
@login_required
@permission_required('seed.can_access_admin')
def delete_organization_buildings(request):
    """
    Starts a background task to delete all BuildingSnapshots
    in an org.

    :GET: Expects 'org_id' for the organization.

    Returns::

        {'status': 'success' or 'error',
         'progress_key': ID of background job, for retrieving job progress
        }
    """
    org_id = request.GET.get('org_id', '')
    return tasks.delete_organization_buildings(org_id)


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def delete_buildings(request):
    """
    Deletes all BuildingSnapshots the user has selected.

    Does not delete selected_buildings where the user is not a member or owner
    of the organization the selected building belongs. Since search shows
    buildings across all the orgs a user belongs, it's possible for a building
    to belong to an org outside of `org_id`.

    :DELETE: Expects 'org_id' for the organization, and the search payload
    similar to add_buildings/create_project

        {
            'organization_id': 2,
            'search_payload': {
                'selected_buildings': [2, 3, 4],
                'select_all_checkbox': False,
                'filter_params': ... // see search_buildings
            }
        }

    Returns::

        {'status': 'success' or 'error'}
    """
    # get all orgs the user is in where the user is a member or owner
    orgs = request.user.orgs.filter(
        organizationuser__role_level__gte=ROLE_MEMBER
    )
    body = json.loads(request.body)
    body = body['search_payload']

    selected_building_ids = body.get('selected_buildings', [])

    if not body.get('select_all_checkbox', False):
        # only get the manually selected buildings
        selected_buildings = get_search_query(request.user, {})
        selected_buildings = selected_buildings.filter(
            pk__in=selected_building_ids,
            super_organization__in=orgs
        )
    else:
        # get all buildings matching the search params minus the de-selected
        selected_buildings = get_search_query(request.user, body)
        selected_buildings = selected_buildings.exclude(
            pk__in=selected_building_ids,
        ).filter(super_organization=orgs)

    tasks.log_deleted_buildings.delay(
        list(selected_buildings.values_list('id', flat=True)), request.user.pk
    )
    # this step might have to move into a task
    CanonicalBuilding.objects.filter(
        buildingsnapshot=selected_buildings
    ).update(active=False)
    return {'status': 'success'}    

import random

#DMcQ: Test for building reporting


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def get_building_summary_report_data(request):
    """ 
    This method returns basic, high-level data about a set of buildings, fitered by organization ID.

    It expects as parameters

    :GET:
    * start_date:       The starting date for the data series with the format  `YYYY-MM-DD`
    * end_date:         The starting date for the data series with the format  `YYYY-MM-DD`

    Returns::
    The returned JSON document that has the following structure.
    ```
            {
                "status": "success",
                "summary_data": 
                {
                    "num_buildings": number of buildings returned from query,
                    "avg_eui": average EUI for returned buildings,
                    "avg_energy_score": average energy score for returned buildings
                }
            }
    ```


    Units for return values are as follows:

    ```
    | property              | units      |
    |-----------------------|------------|
    | avg_eui               | kBtu-ft2   |
    ```
    
    ---

    parameters:
        - name: organization_id
          description: User's organization which should be used to filter building query results
          required: true
          type: string
          paramType: query
        - start_date:
          description: The start date for the entire dataset.
          required: true
          type: string
          paramType: query
        - end_date:
          description: The end date for the entire dataset.
          required: true
          type: string
          paramType: query

    type:            
        status:
            required: true
            type: string
        summary_data:
            required: true
            type: object           


    responseMessages:
        - code: 400
          message: Bad request, only GET method is available
        - code: 401
          message: Not authenticated
        - code: 403
          message: Insufficient rights to call this procedure

    """

    #TODO: Generate this data the right way! Will be implemented by Stephen C. The following is just dummy data...

    if request.method != 'GET':
        return HttpResponseBadRequest("This view replies only to GET methods")

       
    #Read in x and y vars requested by client
    try:
        orgs = [ request.GET.get('organization_id') ] #How should we capture user orgs here?
        from_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
    except Exception, e:
        msg = "Error while calling the API function get_scatter_data_series, missing parameter"
        _log.error(msg)
        _log.exception(str(e))
        return HttpResponseBadRequest(msg)


    num_buildings = BuildingSnapshot.objects.filter(
                super_organization__in=orgs,
                canonicalbuilding__active=True
            ).count()

    avg_eui = 123
    avg_energy_score = 321

    
    data = {    "num_buildings" : num_buildings,
                "avg_eui" : avg_eui,
                "avg_energy_score": avg_energy_score }

    #Send back to client
    return {
        'status': 'success',
        'summary_data' : data
    }
    
    
def get_raw_report_data(from_date, end_date, orgs, x_var, y_var):
    """ This method returns data used to generate graphing reports. It expects as parameters

        * from_date:       The starting date for the data series.  Date object
        * end_date:         The starting date for the data series with the format. Date object
        * x_var:            The variable name to be assigned to the "x" value in the returned data series 
        * y_var:            The variable name to be assigned to the "y" value in the returned data series
        * orgs:  The organizations to be used when querying data.

        The x and y variables should be column names in the BuildingSnapshot table.  In theory they could
        be in the extra_data too and this works but is currently disabled.

        Returns::
        bldg_counts:  dict that looks like {year_ending : {"buidings_with_data" : set(canonical ids), "buidings" : set(canonical ids)}
                        This is a collection of all year_ending dates and ids the canonical buildings that have data for that year and those that
                        have files with that year_ending but no valid data point
                        E.G.
                        "bldg_counts"     (pending)    
                            __len__    int: 8    
                            2000-12-31 (140037191378512)    dict: {'buildings_w_data': set([35897, 35898]), 'buildings': set([35897, 35898])}    
                            2001-12-31 (140037292480784)    dict: {'buildings_w_data': set([35897, 35898]), 'buildings': set([35897, 35898])} 
                        
        data:    dict that looks like {canonical_id : { year_ending : {'x' : x_value, 'y' : y_value', 'release_date' : release_date, 'building_snapshot_id' : building_snapshot_id}}}
                This is the actual data for the building.  The top level key is the canonical_id then the next level is the year_ending and under that
                is the actual data.  NOTE:  If the year has files for a building but no valid data there will be an entry for that year but the
                x and y values will be None.
                
                E.G.
                "data"     (pending)    
                    __len__    int: 2    
                    35897 (28780560)    defaultdict: defaultdict(<type 'dict'>, {datetime.date(2001, 12, 31): {'y': 95.0, 'x': 88.0, 'release_date': datetime.datetime(2001, 12, 31, 0, 0), 'building_snapshot_id': 35854}, datetime.date(2004, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2004, 12, 31, 0, 0), 'building_snapshot_id': 35866}, datetime.date(2003, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2003, 12, 31, 0, 0), 'building_snapshot_id': 35860}, datetime.date(2009, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2009, 12, 31, 0, 0), 'building_snapshot_id': 35884}, datetime.date(2007, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2007, 12, 31, 0, 0), 'building_snapshot_id': 35878}, datetime.date(2000, 12, 31): {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2000, 12, 31, 0, 0), 'building_snapshot_id': 35850}, datetime.date(2010, 12, 31): {'y': 111.0, 'x': 21.0, 'release_date': datetime.datetime(2011, 12, 31, 0, 0...    
                        __len__    int: 8    
                        2000-12-31 (140037191378512)    dict: {'y': 400000.0, 'x': 28.2, 'release_date': datetime.datetime(2000, 12, 31, 0, 0), 'building_snapshot_id': 35850}    
                        2001-12-31 (140037292480784)    dict: {'y': 95.0, 'x': 88.0, 'release_date': datetime.datetime(2001, 12, 31, 0, 0), 'building_snapshot_id': 35854}    
                          
        """

    #year_ending in the BuildingSnapshot model is a DateField which corresponds to a python datetime.date
    #not a datetime.datetime.  Ensure a conversion here
    try:
        from_date = from_date.date()
    except:
        pass

    try:
        end_date = end_date.date()
    except:
        pass

    #First get all building records for the orginization in the date range
    #Can't just look for those that aren't null since one of the things that
    #needs to get reported is how many for a given year do not have data 
    #(i.e. have a null value for either x_var or y_var
    bldgs = BuildingSnapshot.objects.filter(
                super_organization__in=orgs,
                year_ending__gte = from_date,
                year_ending__lte = end_date
            )
             
    #data will be a dict of canonical building id -> year ending -> building data         
    data = defaultdict(lambda: defaultdict(dict))
    
    canonical_buildings = set(bldg.tip for bldg in bldgs)           
    canonical_ids = [x.id for x in canonical_buildings]
        
 
    #if the BuildingSnapshot has the attribute use that directly.  
    #in the future if it should search extra_data but extra_data is still not 
    #searchable directly then this can be adjusted by replacing the last None with
    # obj.extra_data[attr] if hasattr(obj, "extra_data") and attr in obj.extra_data else None
    get_attr_f = lambda obj, attr: getattr(obj, attr) if hasattr(obj, attr) else None
          
    bldg_counts = {}
    
    def process_snapshot(canonical_building_id, snapshot):      
        from datetime import date

        #The data is meaningless here aside if there is no valid year_ending value
        if not hasattr(snapshot, "year_ending"):
            return

        year_ending_year = snapshot.year_ending
        
        if year_ending_year not in bldg_counts:
            bldg_counts[year_ending_year] = {"buildings" : set(), "buildings_w_data" : set()}
        release_date = get_attr_f(snapshot, "release_date")
        
        #if there is no release_date then we have no way of priotizing vs other records with the same
        #year_ending.  Plus it is an indication of something wrong so just exit here 
        if not release_date:            
            return
            
        bldg_counts[year_ending_year]["buildings"].add(canonical_building_id)
            
        if (                 
                (year_ending_year not in data[canonical_building_id]) or 
                (not data[canonical_building_id][year_ending_year]) or
                (data[canonical_building_id][year_ending_year]["release_date"] < release_date)
            ):            
            bldg_x = get_attr_f(snapshot, x_var)
            bldg_y = get_attr_f(snapshot, y_var)
            #what does it mean for a building to "have data"?  I am assuming it must have values for
            #both x and y fields.  Change "and" to "or" to make it either and "True"
            #to return everything
            if bldg_x and bldg_y:
                bldg_counts[year_ending_year]["buildings_w_data"].add(canonical_building_id)
                
                data[canonical_building_id][year_ending_year] = {   "building_snapshot_id" : snapshot.id,
                                                                    "x" : bldg_x,
                                                                    "y" : bldg_y,
                                                                    "release_date" : release_date}
            else:
                try:
                    bldg_counts[year_ending_year]["buildings_w_data"].remove(canonical_building_id)                   
                except:
                    pass
                
                #if this more recent data point does not have both x and y values then the data for the year ending is now invalid
                #mark that here by giving both 'x' and 'y' a value of None
                #can't just delete the year since we need to retain the release_date.  If the most recent 
                #release_date for a given year_ending is not value then that means that year is not valid for the building
            
                data[canonical_building_id][year_ending_year] = {   "building_snapshot_id" : snapshot.id,
                                                                    "x" : None,
                                                                    "y" : None,
                                                                    "release_date" : release_date}
                        
    for canonical_building in canonical_buildings:
        canonical_building_id = canonical_building.id  
        
        if canonical_building.parent_tree:    
            bldg = canonical_building
            #progress up the the tree processing unmerged snapshots until there aren't any more
            while bldg:
                unmerged_snapshots = bldg.parents.filter(parents__isnull = True)
                #get the parent that is merged, if any.  If not then we're done when we finish this iteration
                bldg = bldg.parents.filter(parents__isnull = False).exclude(id = bldg.id)
                if bldg.count():
                    bldg = bldg[0]
                else:
                    bldg = None
                
                #process all unmerged buildings.
                #Note:  I don't really know how this works in terms of order
                #for the root two buildings in the tree
                for unmerged_bs in unmerged_snapshots:
                    #even though the query at the beginning specifies a date range since this is using the tree
                    #some other records without a year_ending may have snuck back in.  Ignore them here.
                    if not hasattr(unmerged_bs, "year_ending") or type(unmerged_bs.year_ending) != datetime.date:
                        continue
                    if from_date <= unmerged_bs.year_ending <= end_date:
                        process_snapshot(canonical_building_id, unmerged_bs)
        else:
            #there is only one record and it is canonical so just process that
            process_snapshot(canonical_building_id, canonical_building)                                                                
    
    return bldg_counts, data


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def get_building_report_data(request):
    """ This method returns a set of x,y building data for graphing. It expects as parameters

        :GET:
        * start_date:       The starting date for the data series with the format  `YYYY-MM-DD`
        * end_date:         The starting date for the data series with the format  `YYYY-MM-DD`
        * x_var:            The variable name to be assigned to the "x" value in the returned data series 
        * y_var:            The variable name to be assigned to the "y" value in the returned data series
        * organization_id:  The organization to be used when querying data.

        The x_var values should be from the following set of variable names:

            - site_eui
            - source_eui
            - site_eui_weather_normalized
            - source_eui_weather_normalized
            - energy_score 

        The y_var values should be from the following set of variable names:

            - gross_floor_area
            - use_description
            - year_built

        This method includes building record count information as part of the result JSON in a property called "building_counts."
        This property provides data on the total number of buildings available in each 'year ending' group, as well as the subset of 
        those buildings that have actual data to graph. By sending these  values in the result 
        we allow the client to easily build a message like "200 of 250 buildings in this group have data."


        Returns::
        The returned JSON document that has the following structure.
        ```
            {
                "status": "success",
                "chart_data": [
                    {
                        "id" the id of the building,
                        "yr_e" : the year ending value for this data point
                        "x": value for x var, 
                        "y": value for y var,                        
                    },
                    ...
                ],
                "building_counts": [
                    {
                        "yr_e": string for year ending 
                        "num_buildings": number of buildings in query results
                        "num_buildings_w_data" : number of buildings with valid data in query results
                    },
                    ...
                ]                               
                "num_buildings": total number of buildings in query results,
                "num_buildings_w_data" : total number of buildings with valid data in the query results
            }
        ```

        ---


        parameters:
            - name: x_var
              description: Name of column in building snapshot database to be used for "x" axis
              required: true
              type: string
              paramType: query
            - name: y_var
              description: Name of column in building snapshot database to be used for "y" axis
              required: true
              type: string
              paramType: query
            - start_date:
              description: The start date for the entire dataset.
              required: true
              type: string
              paramType: query
            - end_date:
              description: The end date for the entire dataset.
              required: true
              type: string
              paramType: query
            - name: organization_id
              description: User's organization which should be used to filter building query results
              required: true
              type: string
              paramType: query              
            - name: aggregate
              description: Aggregates data based on internal rules (given x and y var)
              required: true
              type: string
              paramType: query
  
        type:            
            status:
                required: true
                type: string
            chart_data:
                required: true
                type: array
            num_buildings:
                required: true
                type: string
            num_buildings_w_data:
                required: true
                type: string

        responseMessages:
            - code: 400
              message: Bad request, only GET method is available
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
    
                  
        """

    from dateutil.parser import parse
    from collections import defaultdict

    if request.method != 'GET':
        return HttpResponseBadRequest('This view replies only to GET methods')

    #Read in x and y vars requested by client
    try:
        x_var = request.GET['x_var']
        y_var = request.GET['y_var']
        orgs = [ request.GET['organization_id'] ] #How should we capture user orgs here?
        from_date = request.GET['start_date']
        end_date = request.GET['end_date']

    except Exception, e:
        msg = "Error while calling the API function get_building_report_data, missing parameter"
        _log.error(msg)
        _log.exception(str(e))
        return HttpResponseBadRequest(msg)
    
    valid_values = [
        'site_eui', 'source_eui', 'site_eui_weather_normalized',
        'source_eui_weather_normalized', 'energy_score',
        'gross_floor_area', 'use_description', 'year_built'
    ]

    if x_var not in valid_values or y_var not in valid_values:
        return HttpResponseBadRequest('Invalid fields specified.')

    try:
        from_date = parse(from_date).date()
        end_date = parse(end_date).date()
    except Exception, e:
        msg = "Couldn't convert date strings to date objects"
        _log.error(msg)
        _log.exception(str(e))
        return HttpResponseBadRequest(msg)

    bldg_counts, data = get_raw_report_data(from_date, end_date, orgs, x_var, y_var)
    #    now we have data as nested dictionaries like canonical_building_id -> year_ending -> {building_snapshot_id, address_line_1, x, y}
    #    but the comment at the beginning o says to do it like a list of dicts that looks like
    #                     "chart_data": [
    #                     {
    #                         "id" the id of the building,
    #                         "yr_e" : the year ending value for this data point
    #                         "x": value for x var, 
    #                         "y": value for y var,                        
    #                     },
    #                     ...
    #                 ],

    chart_data = []
    building_counts = []
    for year_ending, values in bldg_counts.items():
        buildingCountItem = {   "num_buildings"         : len(values["buildings"]), 
                                "num_buildings_w_data"  : len(values["buildings_w_data"]),
                                "yr_e"                  : year_ending.strftime('%Y-%m-%d')
                            }
        building_counts.append(buildingCountItem)
    
    for canonical_id, year_ending_to_data_map in data.iteritems():
        for year_ending, requested_data in year_ending_to_data_map.iteritems():
            d = requested_data 
            #The point must have both an x and a y value or else it is not valid
            if not (d["x"] and d["y"]):
                continue        
            d["id"] = canonical_id
            d["yr_e"] = year_ending.strftime('%Y-%m-%d')
            chart_data.append(d)


    #Send back to client
    return {    'status': 'success',
                'chart_data' : chart_data,
                'building_counts' : building_counts  
           }

from itertools import groupby
from operator import itemgetter
import random

@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def get_aggregated_building_report_data(request):
    """ This method returns a set of aggregated building data for graphing. It expects as parameters

        :GET:
        * start_date:       The starting date for the data series with the format  `YYYY-MM-DDThh:mm:ss+hhmm`
        * end_date:         The starting date for the data series with the format  `YYYY-MM-DDThh:mm:ss+hhmm`
        * x_var:            The variable name to be assigned to the "x" value in the returned data series 
        * y_var:            The variable name to be assigned to the "y" value in the returned data series
        * organization_id:  The organization to be used when querying data.

        The x_var values should be from the following set of variable names:

            - site_eui
            - source_eui
            - site_eui_weather_normalized
            - source_eui_weather_normalized
            - energy_score 

        The y_var values should be from the following set of variable names:

            - gross_floor_area
            - use_description
            - year_built

        This method includes building record count information as part of the result JSON in a property called "building_counts."
        This property provides data on the total number of buildings available in each 'year ending' group, as well as the subset of 
        those buildings that have actual data to graph. By sending these  values in the result 
        we allow the client to easily build a message like "200 of 250 buildings in this group have data."


        Returns::
        The returned JSON document that has the following structure.
        ```
            {
                "status": "success",
                "chart_data": [
                    {
                        "yr_e": x - group by year ending
                        "x" : x, - median value in group
                        "y" : y - average value thing
                    },
                    {
                        "yr_e": x
                        "x" : x,
                        "y" : y
                    }       
                    ...
                ],
                "building_counts": [
                    {
                        "yr_e": string for year ending - group by
                        "num_buildings": number of buildings in query results
                        "num_buildings_w_data" : number of buildings with valid data in this group, BOTH x and y?
                    },
                    ...
                ]                              
                "num_buildings": total number of buildings in query results,
                "num_buildings_w_data" : total number of buildings with valid data in query results
            }
        ```

        ---


        parameters:
            - name: x_var
              description: Name of column in building snapshot database to be used for "x" axis
              required: true
              type: string
              paramType: query
            - name: y_var
              description: Name of column in building snapshot database to be used for "y" axis
              required: true
              type: string
              paramType: query
            - start_date:
              description: The start date for the entire dataset.
              required: true
              type: string
              paramType: query
            - end_date:
              description: The end date for the entire dataset.
              required: true
              type: string
              paramType: query
            - name: organization_id
              description: User's organization which should be used to filter building query results
              required: true
              type: string
              paramType: query        
  
        type:            
            status:
                required: true
                type: string
            chart_data:
                required: true
                type: array
            building_counts:
                required: true
                type: array
            num_buildings:
                required: true
                type: string
            num_buildings_w_data:
                required: true
                type: string

        responseMessages:
            - code: 400
              message: Bad request, only GET method is available
            - code: 401
              message: Not authenticated
            - code: 403
              message: Insufficient rights to call this procedure
    
                  
        """


    #TODO: Generate this data the right way! The following is just dummy data...
    if request.method != 'GET':
        return HttpResponseBadRequest('This view replies only to GET methods')

    #Read in x and y vars requested by client
    try:
        x_var = request.GET['x_var']
        y_var = request.GET['y_var']
        orgs = [ request.GET['organization_id'] ] #How should we capture user orgs here?
        from_date = request.GET['start_date']
        end_date = request.GET['end_date']
    except KeyError, e:
        msg = "Error while calling the API function get_aggregated_building_report_data, missing parameter"
        _log.error(msg)
        _log.exception(str(e))
        return HttpResponseBadRequest(msg)

    valid_x_var_values = [
        'site_eui', 'source_eui', 'site_eui_weather_normalized',
        'source_eui_weather_normalized', 'energy_score'
    ]

    valid_y_var_values = [
        'gross_floor_area', 'use_description', 'year_built'
    ]

    if x_var not in valid_x_var_values or y_var not in valid_y_var_values:
        return HttpResponseBadRequest('Invalid fields specified.')

    dt_from = None
    dt_to = None
    try:
        dt_from = parse(from_date)
        dt_to = parse(end_date)
    except Exception, e:
        msg = "Couldn't convert date strings to date objects"
        _log.error(msg)
        _log.exception(str(e))
        return HttpResponseBadRequest(msg) 

    _, data = get_raw_report_data(dt_from, dt_to, orgs, x_var, y_var)

    # Grab building snapshot ids from get_raw_report_data payload.
    snapshot_ids = []
    for k, v in data.items():
        for date, building in v.items():
            snapshot_ids.append(building['building_snapshot_id'])

    bldgs = BuildingSnapshot.objects.filter(pk__in=snapshot_ids)

    grouped_buildings = defaultdict(list)
    for building in bldgs:
        grouped_buildings[building.year_ending].append(building)

    chart_data = []
    building_counts = []
    for year_ending, buildings in grouped_buildings.items():
        yr_e = year_ending.strftime('%b %d, %Y') # Dec 31, 2011

        # Begin filling out building_counts object.

        building_count_item = {
            'yr_e': yr_e,
            'num_buildings': len(buildings),
            'num_buildings_w_data': 0
        }

        # Tally which buildings have both fields set.
        for b in buildings:
            if getattr(b, x_var) and getattr(b, y_var):
                building_count_item['num_buildings_w_data'] += 1

        building_counts.append(building_count_item)

        # End of building_counts object creation, begin filling out chart_data object.

        if y_var == 'use_description':

            # Group buildings in this year_ending group into uses
            grouped_uses = defaultdict(list)
            for b in buildings:
                if not getattr(b, y_var):
                    continue
                grouped_uses[str(getattr(b, y_var)).lower()].append(b)

            # Now iterate over use groups to make each chart item
            for use, buildings_in_uses in grouped_uses.items():
                chart_data.append({
                    'yr_e': yr_e,
                    'x': median([getattr(b, x_var) for b in buildings_in_uses if getattr(b, x_var)]),
                    'y': use.capitalize()
                })

        elif y_var == 'year_built':

            # Group buildings in this year_ending group into decades
            grouped_decades = defaultdict(list)
            for b in buildings:
                if not getattr(b, y_var):
                    continue
                grouped_decades['%s0' % str(getattr(b, y_var))[:-1]].append(b)

            # Now iterate over decade groups to make each chart item
            for decade, buildings_in_decade in grouped_decades.items():
                chart_data.append({
                    'yr_e': yr_e,
                    'x': median([getattr(b, x_var) for b in buildings_in_decade if getattr(b, x_var)]),
                    'y': '%s-%s' % (decade, '%s9' % str(decade)[:-1]) # 1990-1999
                })

        elif y_var == 'gross_floor_area':
            y_display_map = {
                0: '0-99k',
                100000: '100-199k',
                200000: '200k-299k',
                300000: '300k-399k',
                400000: '400-499k',
                500000: '500-599k',
                600000: '600-699k',
                700000: '700-799k',
                800000: '800-899k',
                900000: '900-999k',
                1000000: 'over 1,000k',
            }

            # Group buildings in this year_ending group into ranges
            grouped_ranges = defaultdict(list)
            for b in buildings:
                if not getattr(b, y_var):
                    continue
                area = getattr(b, y_var)
                grouped_ranges[round_down_hundred_thousand(area)].append(b)

            # Now iterate over range groups to make each chart item
            for range_floor, buildings_in_range in grouped_ranges.items():
                chart_data.append({
                    'yr_e': yr_e,
                    'x': median([getattr(b, x_var) for b in buildings_in_range if getattr(b, x_var)]),
                    'y': y_display_map[range_floor]
                })

    #Send back to client
    return {
        'status': 'success',
        'chart_data' : chart_data,
        'building_counts' : building_counts
    }
