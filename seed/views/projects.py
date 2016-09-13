# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# system imports
import datetime
import logging

# django imports
from seed.utils.cache import get_cache

# vendor imports
from dateutil import parser

# config imports
from seed.tasks import (
    add_buildings,
    remove_buildings,
)

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    Compliance,
    Project,
    ProjectBuilding,
    StatusLabel,
)
from seed.utils.api import api_endpoint_class

from seed.utils import projects as utils
from seed.utils.time import convert_to_js_timestamp

from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets, status
from rest_framework.decorators import list_route
from rest_framework.authentication import SessionAuthentication
from seed.authentication import SEEDAuthentication


_log = logging.getLogger(__name__)

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name'
]


class ProjectsViewSet(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        Retrieves all projects for a given organization.

        :GET: Expects organization_id in query string.

        Returns::

            {
                'status': 'success',
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
                    }...
                ]
            }
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        """
        organization_id = request.query_params.get('organization_id', None)
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

        return JsonResponse({'status': 'success', 'projects': projects})

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def get_project(self, request):
        """
        Retrieves details about a project.
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: project_slug
              description: The project slug identifier for this project
              required: true
              paramType: query
        """
        """
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
        project_slug = request.query_params.get('project_slug', None)
        if project_slug is None:
            return JsonResponse({'status': 'error',
                                 'message': 'project_slug needs to be included as a query parameter'},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(slug=project_slug)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not access project with slug = ' + str(project_slug)},
                                status=status.HTTP_404_NOT_FOUND)
        if project.super_organization_id != int(request.query_params.get('organization_id', None)):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
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

        return JsonResponse({'status': 'success', 'project': project_dict})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['DELETE'])
    def delete_project(self, request):
        """
        Deletes a project.
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: "The organization_id"
              required: true
              paramType: query
            - name: project_slug
              description: The project slug identifier for this project
              required: true
              paramType: query
        type:
            status:
                required: true
                type: string
                description: success or error
            message:
                required: false
                description: An error message, if any
                type: string
        """
        organization_id = request.query_params.get('organization_id', None)
        project_slug = request.query_params.get('project_slug', None)
        if organization_id is None or project_slug is None:
            return JsonResponse({'status': 'error',
                                 'message': 'Needs organization_id and project_slug as query parameters.'},
                                status=status.HTTP_400_BAD_REQUEST)
        project = Project.objects.get(slug=project_slug)
        if project.super_organization_id != int(organization_id):
            return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        project.delete()
        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def create(self, request):
        """
        Creates a new project.
        @TODO: What's a compliance_type?
        ---
        parameters:
            - name: organization_id
              description: ID of organization to associate new project with
              type: integer
              required: true
              paramType: query
            - name: name
              description: name of the new project
              type: string
              required: true
            - name: compliance_type
              description: description of type of compliance
              type: string
              required: true
            - name: description
              description: description of new project
              type: string
              required: true
            - name: end_date
              description: Timestamp for when project ends
              type: string
              required: true
            - name: deadline_date
              description: Timestamp for compliance deadline
              type: string
              required: true
        type:
            status:
                required: true
                type: string
                description: "'success' if the call succeeds"
            message:
                required: false
                type: string
                description: error message, if any
            project_slug:
                required: true
                type: string
                description: identifier of new project, if successfully created
        """
        body = request.data
        project_name = body.get('name')
        org_id = request.query_params.get('organization_id', None)
        project_description = body.get('description')

        if Project.objects.filter(
            name=project_name,
            super_organization_id=org_id
        ).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'project already exists for user'
            }, status=status.HTTP_409_CONFLICT)

        project, created = Project.objects.get_or_create(
            name=project_name,
            owner=request.user,
            super_organization_id=org_id,
        )
        if not created:
            return JsonResponse({
                'status': 'error',
                'message': 'project already exists for the organization'
            }, status=status.HTTP_409_CONFLICT)
        project.last_modified_by = request.user
        if project_description:
            project.description = project_description
        else:
            project.description = ""
        project.save()

        project_compliance_type = body.get('compliance_type', None)
        project_end_date = body.get('end_date', None)
        project_deadline_date = body.get('deadline_date', None)

        if all(v is not None for v in (project_compliance_type, project_end_date, project_deadline_date)):
            c = Compliance(project=project)
            c.compliance_type = project_compliance_type
            c.end_date = parser.parse(project_end_date)
            c.deadline_date = parser.parse(project_deadline_date)
            c.save()

        return JsonResponse({'status': 'success', 'project_slug': project.slug})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['PUT'])
    def update_project(self, request):
        """
        Updates an existing project's details and compliance info.
        ---
        parameter_strategy: replace
        parameters:
            - name: project_slug
              description: Project slug identifier
              required: true
              paramType: query
            - name: name
              description: updated name of the project, if rename is requested
              type: string
              required: false
            - name: is_compliance
              description: true/false flag for whether this is a compliance project
              type: bool
              required: true
            - name: end_date
              description: If is_compliance is true, this is the updated compliance end date
              type: datetime
              required: false
            - name: deadline_date
              description: If is_compliance is true, this is the updated compliance deadline date
              type: datetime
              required: false
        type:
            status:
                required: true
                type: string
                description: success or error
            message:
                required: false
                description: An error message, if any
                type: string
        """
        body = request.data
        project_name = body.get('name', None)
        project_slug = request.query_params.get('project_slug', None)
        if project_slug is None:
            return JsonResponse({'status': 'error',
                                 'message': 'project_slug must be passed in as query argument'},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(slug=project_slug)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve project with slug = ' + str(project_slug)},
                                status=status.HTTP_404_NOT_FOUND)
        if project_name:
            project.name = project_name
        project.last_modified_by = request.user
        project.save()

        project_compliance_type = body.get('is_compliance')
        if project_compliance_type:  # don't do any changes if new compliance flag isn't included
            if project_compliance_type.lower() == "true":
                if project.has_compliance:
                    c = project.get_compliance()
                else:
                    c = Compliance.objects.create(
                        project=project,
                    )
                project_end_date = body.get('end_date')
                project_deadline_date = body.get('deadline_date')
                c.end_date = parser.parse(project_end_date)
                c.deadline_date = parser.parse(project_deadline_date)
                c.compliance_type = project_compliance_type
                c.save()
            elif project.has_compliance:
                # delete compliance
                c = project.get_compliance()
                c.delete()

        return JsonResponse({
            'status': 'success',
            'message': 'project %s updated' % project.name
        })

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['PUT'])
    def add_buildings(self, request):
        """
        Adds buildings to a project.
        ---
        parameter_strategy: replace
        parameters:
            - name: project_slug
              required: true
              description: Project slug identifier
              paramType: query
            - name: selected_buildings
              required: true
              description: JSON list of building IDs to add to this project
              many: array[int]
              paramType: body
        type:
            status:
                required: true
                type: string
                description: success or error
            message:
                required: false
                type: string
                description: optional error message, if any
            project_loading_cache_key:
                required: false
                type: string
                description: if adding is initiated, this is an identifier for the
                             background job, to determine the job's progress
        """
        body = request.data
        project_slug = request.query_params.get('project_slug', None)
        if project_slug is None:
            return JsonResponse({'status': 'error',
                                 'message': 'project_slug needs to be included as a query parameter'},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(slug=project_slug)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not find project with project_slug = ' + str(project_slug)},
                                status=status.HTTP_404_NOT_FOUND)
        add_buildings.delay(
            project_slug=project.slug, prpoject_dict=body,
            user_pk=request.user.pk)

        key = project.adding_buildings_status_percentage_cache_key
        return JsonResponse({
            'status': 'success',
            'project_loading_cache_key': key
        })

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @list_route(methods=['PUT'])
    def remove_buildings(self, request):
        """
        Removes buildings from a project.
        ---
        parameter_strategy: replace
        parameters:
            - name: project_slug
              required: true
              description: Project slug identifier
              paramType: query
            - name: selected_buildings
              required: true
              description: JSON list of building IDs to remove from this project
              many: array[int]
              paramType: body
        type:
            status:
                required: true
                type: string
                description: success or error
            message:
                required: false
                type: string
                description: optional error message, if any
            project_removing_cache_key:
                required: false
                type: string
                description: if removing is initiated, this is an identifier for the
                             background job, to determine the job's progress
        """
        body = request.data
        project_slug = request.query_params.get('project_slug', None)
        if project_slug is None:
            return JsonResponse({'status': 'error',
                                 'message': 'project_slug needs to be included as a query parameter'},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            project = Project.objects.get(slug=project_slug)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not find project with project_slug = ' + str(project_slug)},
                                status=status.HTTP_404_NOT_FOUND)
        remove_buildings.delay(
            project_slug=project.slug, project_dict=body,
            user_pk=request.user.pk)
        key = project.removing_buildings_status_percentage_cache_key
        return JsonResponse({
            'status': 'success',
            'project_removing_cache_key': key
        })

    # TODO: Broad except clause; what will redis return?
    @api_endpoint_class
    @ajax_request_class
    @list_route(methods=['GET'])
    def add_building_status(self, request):
        """
        Returns percentage complete of background task for adding building to project.
        ---
        parameter_strategy: replace
        parameters:
            - name: project_loading_cache_key
              required: true
              description:  Job identifier from add_buildings_to_project.
              type: string
              paramType: query
        type:
            status:
                required: true
                type: string
                description: success or error
            project_object:
                required: false
                type: object
                description: descriptive object for progress status
        """

        body = request.data
        project_loading_cache_key = body.get('project_loading_cache_key')

        try:
            progress_object = get_cache(project_loading_cache_key)
        except:
            msg = "Couldn't find project loading key %s in cache " % project_loading_cache_key
            _log.error(msg)
            raise Exception(msg)

        return JsonResponse({
            'status': 'success',
            'progress_object': progress_object
        })

    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def count(self, request):
        """
        Returns the number of projects within the org tree to which
        a user belongs.  Counts projects in parent orgs and sibling orgs.
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
            project_count:
                required: true
                type: integer
                description: count of projects
        """
        org_id = request.query_params.get('organization_id', None)
        projects_count = Project.objects.filter(super_organization_id=org_id).distinct().count()
        return JsonResponse({'status': 'success', 'projects_count': projects_count})

    @api_endpoint_class
    @ajax_request_class
    @list_route(methods=['PUT'])
    def update_building(self, request):
        """
        Updates extra information about the building/project relationship.
        In particular, whether the building is compliant and who approved it.
        ---
        parameter_strategy: replace
        parameters:
            - name: project_slug
              required: true
              description: Project slug identifier
              paramType: query
            - name: building_id
              required: true
              description: id of building to update
              type: integer
            - name: label
              required: true
              description: Identifier of label to apply
              type: string
        type:
            status:
                required: true
                type: string
                description: success or error
            message:
                required: false
                type: string
                description: error message, if any
            approved_date:
                required: false
                type: string
                description: Timestamp of change (now)
            approver:
                required: false
                type: string
                description: Email address of user making change
        """
        body = request.data
        project_slug = request.query_params.get('project_slug', None)
        if project_slug is None:
            return JsonResponse({'status': 'error',
                                 'message': 'project_slug needs to be included as a query parameter'},
                                status=status.HTTP_400_BAD_REQUEST)
        try:
            pb = ProjectBuilding.objects.get(
                project__slug=project_slug,
                building_snapshot__pk=body['building_id'])
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not access project building with slug = ' + str(project_slug)},
                                status=status.HTTP_404_NOT_FOUND)
        pb.approved_date = datetime.datetime.now()
        pb.approver = request.user
        status_label = StatusLabel.objects.get(pk=body['label'])
        pb.status_label = status_label
        pb.save()
        return JsonResponse({
            'status': 'success',
            'approved_date': pb.approved_date.strftime("%m/%d/%Y"),
            'approver': pb.approver.email,
        })

    @api_endpoint_class
    @ajax_request_class
    @list_route(methods=['PUT'])
    def move_buildings(self, request):
        """
        Moves buildings from one project to another.
        ---
        parameter_strategy: replace
        parameters:
            - name: buildings
              description: JSON array, list of buildings to be moved
              many: array[int]
              required: true
            - name: copy
              description: true to copy the buildings, false to move,
              type: bool
              required: true
            - name: select_all_checkbox
              description: true to select all checkboxes
              type: bool
              required: true
            - name: source_project_slug
              description: Source Project primary key
              type: integer
              required: true
            - name: target_project_slug
              description: Target Project primary key
              type: integer
              required: true
            - name: search_params
              description: JSON body containing: filter_params__project_slug, project_slug, and q
              type: object
              required: true
        type:
            status:
                type: string
                description: success if successful
                required: true
        """
        body = request.data

        utils.transfer_buildings(
            source_project_slug=body['source_project_slug'],
            target_project_slug=body['target_project_slug'],
            buildings=body['buildings'],
            select_all=body['select_all_checkbox'],
            search_params=body['search_params'],
            user=request.user,
            copy_flag=body['copy']
        )
        return JsonResponse({'status': 'success'})
