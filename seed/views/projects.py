"""
:copyright: (c) 2014 Building Energy Inc
"""
# system imports
import json
import datetime

# django imports
from django.contrib.auth.decorators import login_required
from django.core.cache import cache

# vendor imports
from annoying.decorators import ajax_request
from dateutil import parser


# config imports
from seed.tasks import (
    add_buildings,
    remove_buildings,
)

from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import (
    Compliance,
    Project,
    ProjectBuilding,
    StatusLabel,
)
from seed.utils.api import api_endpoint

from ..utils import projects as utils
from ..utils.time import convert_to_js_timestamp


DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name'
]


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_projects(request):
    """
    Retrieves all projects for a given organization.

    :GET: Expects organization_id in query string.

    Returns::

        {'status': 'success',
         'projects': [
            {
             'name': project's name,
             'slug': project's identifier,
             'status': 'active',
             'number_of_buildings': Count of buildings associated with project
             'last_modified': Timestamp when project last changed
             'last_modified_by': {
                'first_name': first name of user that made last change,
                'last_name': last name,
                'email': email address,
                },
             'is_compliance': True if project is a compliance project,
             'compliance_type': Description of compliance type,
             'deadline_date': Timestamp of when compliance is due,
             'end_date': Timestamp of end of project
            }
            ...
          ]
    }
    """
    organization_id = request.GET.get('organization_id', '')
    projects = []

    for p in Project.objects.filter(
        super_organization_id=organization_id,
    ).distinct():
        if p.last_modified_by:
            first_name = p.last_modified_by.first_name
            last_name = p.last_modified_by.last_name
            email = p.last_modified_by.email
        else:
            first_name = None
            last_name = None
            email = None
        p_as_json = {
            'name': p.name,
            'slug': p.slug,
            'status': 'active',
            'number_of_buildings': p.project_building_snapshots.count(),
            # convert to JS timestamp
            'last_modified': int(p.modified.strftime("%s")) * 1000,
            'last_modified_by': {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
            },
            'is_compliance': p.has_compliance,
        }
        if p.has_compliance:
            compliance = p.get_compliance()
            p_as_json['end_date'] = convert_to_js_timestamp(
                compliance.end_date)
            p_as_json['deadline_date'] = convert_to_js_timestamp(
                compliance.deadline_date)
            p_as_json['compliance_type'] = compliance.compliance_type
        projects.append(p_as_json)

    return {'status': 'success', 'projects': projects}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_project(request):
    """
    Retrieves details about a project.

    :GET: Expects the project's identifier (slug) as project_slug in the
        query string.
        Expects an organization_id (to which project belongs) in the query
        string.

    Returns::

        {
         'name': project's name,
         'slug': project's identifier,
         'status': 'active',
         'number_of_buildings': Count of buildings associated with project
         'last_modified': Timestamp when project last changed
         'last_modified_by': {
            'first_name': first name of user that made last change,
            'last_name': last name,
            'email': email address,
            },
         'is_compliance': True if project is a compliance project,
         'compliance_type': Description of compliance type,
         'deadline_date': Timestamp of when compliance is due,
         'end_date': Timestamp of end of project
        }

    """
    project_slug = request.GET.get('project_slug', '')
    organization_id = request.GET.get('organization_id', '')
    project = Project.objects.get(slug=project_slug)
    if project.super_organization_id != int(organization_id):
        return {'status': 'error', 'message': 'Permission denied'}
    project_dict = project.__dict__
    project_dict['is_compliance'] = project.has_compliance
    if project_dict['is_compliance']:
        c = project.get_compliance()
        project_dict['end_date'] = convert_to_js_timestamp(c.end_date)
        project_dict['deadline_date'] = convert_to_js_timestamp(
            c.deadline_date)
        project_dict['compliance_type'] = c.compliance_type
    del(project_dict['_state'])
    del(project_dict['modified'])
    del(project_dict['created'])

    return {'status': 'success', 'project': project_dict}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def delete_project(request):
    """
    Deletes a project.

    Payload::

        {
         'project_slug': identifier (slug) for the project
         'organization_id': ID of the org the project belongs to
        }

    Returns::

        {
         'status': 'success or error',
         'message': 'error message, if any'
        }

    """
    body = json.loads(request.body)
    project_slug = body.get('project_slug', '')
    organization_id = body.get('organization_id')
    project = Project.objects.get(slug=project_slug)
    if project.super_organization_id != int(organization_id):
        return {'status': 'error', 'message': 'Permission denied'}
    project.delete()
    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def create_project(request):
    """
    Creates a new project.
    @TODO: What's a compliance_type?

    Payload::

        {
         'organization_id': ID of org to associate new project with,
         'project': {
           'name': name of new project,
           'compliance_type': description of type of compliance,
           'description': description of new project,
           'end_date': Timestamp for when project ends,
           'deadline_date': Timestamp for compliance deadline
         }
        }

    Returns::

        {
         'status': 'success' or 'error',
         'message': 'error message, if any',
         'project_slug': Identifier of new project, if project successfully
                         created
        }

    """
    body = json.loads(request.body)
    project_json = body.get('project')

    if Project.objects.filter(
        name=project_json['name'],
        super_organization_id=body['organization_id']
    ).exists():
        return {
            'status': 'error',
            'message': 'project already exists for user'
        }

    project, created = Project.objects.get_or_create(
        name=project_json['name'],
        owner=request.user,
        super_organization_id=body['organization_id'],
    )
    if not created:
        return {
            'status': 'error',
            'message': 'project already exists for the organization'
        }
    project.last_modified_by = request.user
    project.description = project_json.get('description')
    project.save()

    compliance_type = project_json.get('compliance_type', None)
    end_date = project_json.get('end_date', None)
    deadline_date = project_json.get('deadline_date', None)
    if ((compliance_type is not None
         and end_date is not None
         and deadline_date is not None)):
        c = Compliance(project=project)
        c.compliance_type = compliance_type
        c.end_date = parser.parse(project_json['end_date'])
        c.deadline_date = parser.parse(project_json['deadline_date'])
        c.save()

    return {'status': 'success', 'project_slug': project.slug}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def add_buildings_to_project(request):
    """
    Adds buildings to a project.

    Payload::

        {
         'project':
             {
              'project_slug': Identifier of project to add buildings to,
              'selected_buildings': A list of building IDs to add to project
             }
        }

    Returns::

        {
         'status': 'success' or 'error',
         'message': 'error message, if any',
         'project_loading_cache_key': Identifier for the background job, to
             determine the job's progress
        }

    """
    body = json.loads(request.body)
    project_json = body.get('project')
    project = Project.objects.get(slug=project_json['project_slug'])
    add_buildings.delay(
        project_slug=project.slug, project_dict=project_json,
        user_pk=request.user.pk)

    key = project.adding_buildings_status_percentage_cache_key
    return {
        'status': 'success',
        'project_loading_cache_key': key
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def remove_buildings_from_project(request):
    """
    Removes buildings from a project.

    Payload::

        {
         'project':
             {
              'project_slug': Identifier of project to remove buildings from,
              'selected_buildings': A list of building IDs to remove
             }
        }

    Returns::

        {
         'status': 'success' or 'error',
         'message': 'error message, if any',
         'project_removing_cache_key': Identifier for the background job, to
             determine the job's progress
        }

    """
    body = json.loads(request.body)
    project_json = body.get('project')
    project = Project.objects.get(slug=project_json['slug'])
    remove_buildings.delay(
        project_slug=project.slug, project_dict=project_json,
        user_pk=request.user.pk)

    key = project.removing_buildings_status_percentage_cache_key
    return {
        'status': 'success',
        'project_removing_cache_key': key
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def update_project(request):
    """
    Updates an existing project's details and compliance info.

    Payload::

        {
         'project': {
           'project_slug': Identifier of project to update,
           'name': new name for project,
           'is_compliance': true or false,
           'compliance_type': (optional if 'is_compliance' is false)
                description of type of compliance,
           'end_date': (optional if 'is_compliance' is false) Timestamp for
                when project ends,
           'deadline_date': (optional if 'is_compliance' is false) Timestamp
                for compliance deadline
         }
        }

    Returns::

        {
         'status': 'success' or 'error',
         'message': 'error message, if any'
        }

    """
    body = json.loads(request.body)
    project_json = body.get('project')
    project = Project.objects.get(slug=project_json['slug'])
    project.name = project_json['name']
    project.last_modified_by = request.user
    project.save()

    if project_json['is_compliance']:
        if project.has_compliance:
            c = project.get_compliance()
        else:
            c = Compliance.objects.create(
                project=project,
            )
        c.end_date = parser.parse(project_json['end_date'])
        c.deadline_date = parser.parse(project_json['deadline_date'])
        c.compliance_type = project_json['compliance_type']
        c.save()
    elif not project_json['is_compliance'] and project.has_compliance:
        # delete compliance
        c = project.get_compliance()
        c.delete()

    return {
        'status': 'success',
        'message': 'project %s updated' % project.name
    }


@api_endpoint
@ajax_request
@login_required
def get_adding_buildings_to_project_status_percentage(request):
    """
    Returns percentage complete of background task for
    adding building to project.

    Payload::

        {'project_loading_cache_key': Job identifier from
            add_buildings_to_project.
        }

    Returns::
        {'status': 'success',
         'progress_object': {
             'percentage_done': percent job done,
             'numerator': number buildings added,
             'denominator': total number of building to add
         }
        }

    """
    body = json.loads(request.body)
    project_loading_cache_key = body.get('project_loading_cache_key')

    return {
        'status': 'success',
        'progress_object': cache.get(project_loading_cache_key)
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_viewer')
def get_projects_count(request):
    """
    Returns the number of projects within the org tree to which
    a user belongs.  Counts projects in parent orgs and sibling orgs.

    :GET: Expects organization_id for the user's org.

    Returns::

        {
         'status': 'success',
         'projects_count': count of projects
        }

    """
    organization_id = request.GET.get('organization_id', '')
    projects_count = Project.objects.filter(
        super_organization_id=organization_id
    ).distinct().count()

    return {'status': 'success', 'projects_count': projects_count}


@api_endpoint
@ajax_request
@login_required
def update_project_building(request):
    """
    Updates extra information about the building/project relationship.
    In particular, whether the building is compliant and who approved it.

    Payload::

        {
         'project_slug': identifier of project,
         'building_id': ID of building,
         'label': {
                  'id': Identifier of label to apply.
                  }
        }

    Returns::

        {
         'status': 'success',
         'approved_date': Timestamp of change (now),
         'approver': Email address of user making change.
        }

    """
    body = json.loads(request.body)
    pb = ProjectBuilding.objects.get(
        project__slug=body['project_slug'],
        building_snapshot__pk=body['building_id'])
    pb.approved_date = datetime.datetime.now()
    pb.approver = request.user
    status_label = StatusLabel.objects.get(pk=body['label']['id'])
    pb.status_label = status_label
    pb.save()
    return {
        'status': 'success',
        'approved_date': pb.approved_date.strftime("%m/%d/%Y"),
        'approver': pb.approver.email,
    }


@api_endpoint
@ajax_request
@login_required
def move_buildings(request):
    """
    Moves buildings from one project to another.

    Payload::

        {
         "buildings": [
                "00010811",
                "00010809"
            ],
            "copy": true to copy the buildings, false to move,
            "search_params": {
                "filter_params": {
                    "project__slug": "proj-1"
                },
                "project_slug": 34,
                "q": "hotels"
            },
            "select_all_checkbox": false,
            "source_project_slug": "proj-1",
            "target_project_slug": "proj-2"
        }

    Returns::

        {'status': 'success'}

    """
    body = json.loads(request.body)

    utils.transfer_buildings(
        source_project_slug=body['source_project_slug'],
        target_project_slug=body['target_project_slug'],
        buildings=body['buildings'],
        select_all=body['select_all_checkbox'],
        search_params=body['search_params'],
        user=request.user,
        copy_flag=body['copy']
    )
    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
def get_labels(request):
    """
    Gets all labels for any organization the user has access to.

    Returns::

        {
         'status': 'success',
         'labels':
          [
            {
             'name': name of label,
             'color': color of label,
             'id': label's ID
            }, ...
         ]
        }
    """
    labels = utils.get_labels(request.user)
    return {'status': 'success', 'labels': labels}


@api_endpoint
@ajax_request
@login_required
def add_label(request):
    """
    Creates a new label.

    Payload::

        {
         'label':
          {
           "color": "red",
           "name": "non compliant"
          }
        }

    Returns::

        {
         'status': 'success',
         'label_id': The ID of the new label.
        }

    """
    body = json.loads(request.body)
    label = body['label']
    status_label, created = StatusLabel.objects.get_or_create(
        # need a better way to get this, maybe one per org
        super_organization=request.user.orgs.all()[0],
        name=label['name'],
        color=label['color'],
    )
    return {'status': 'success',
            'label_id': status_label.pk}


@api_endpoint
@ajax_request
@login_required
def update_label(request):
    """
    Updates a label.

    Payload::

        {
         "label": {
            "color": Label's new color,
            "id": ID of label to change,
            "name": Label's new name,
         }
        }

    Returns::

        {'status': 'success'}

    """
    body = json.loads(request.body)
    label = body['label']
    status_label = StatusLabel.objects.get(pk=label['id'])
    status_label.color = label['color']
    status_label.name = label['name']
    status_label.save()
    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
def delete_label(request):
    """
    Deletes a label.

    Payload::

        {'label':
         {'id': ID of label to delete}
        }

    Returns::

        {'status': 'success'}

    """
    body = json.loads(request.body)
    label = body['label']
    status_label = StatusLabel.objects.get(pk=label['id'])
    ProjectBuilding.objects.filter(
        status_label=status_label
    ).update(status_label=None)

    status_label.delete()
    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
def apply_label(request):
    """
    Applies a label to buildings (within a project).

    Payload::

        {
         "buildings": [
                "00010811",
                "00010809"
            ],
         "label": {"id": 1 },
         "project_slug": "proj-1",
         "search_params": {
            "filter_params": {
                "project__slug": "proj-1"
                },
                "project_slug": 34,
                "q": ""
            },
            "select_all_checkbox": false
        }

    Returns::

        {'status': 'success'}

    """
    body = json.loads(request.body)

    utils.apply_label(
        project_slug=body['project_slug'],
        buildings=body['buildings'],
        select_all=body['select_all_checkbox'],
        label=body['label'],
        search_params=body['search_params'],
        user=request.user,
    )
    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
def remove_label(request):
    """
    Removes labels from buildings (within a project).

    Payload::

        {
         "buildings": [
                "IMP75-0004N0027"
            ],
         "project_slug": "proj-1",
         "search_params": {
            "filter_params": {
                "project__slug": "proj-1"
                },
                "project_slug": 34,
                "q": ""
            },
            "select_all_checkbox": false
        }

    Returns::

        {'status': 'success'}

    """
    body = json.loads(request.body)

    ProjectBuilding.objects.filter(
        project__pk=body['project']['id'],
        building_snapshot__pk=body['building']['id']
    ).update(
        status_label=None
    )

    return {'status': 'success'}
