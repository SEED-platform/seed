# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# system imports
import logging

from dateutil import parser
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import list_route
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from seed import search
from seed.authentication import SEEDAuthentication
from seed.decorators import (
    DecoratorMixin
)
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import (
    COMPLIANCE_CHOICES,
    STATUS_CHOICES
)
from seed.models import (
    Compliance,
    Project,
    ProjectPropertyView,
    ProjectTaxLotView,
    PropertyView,
    TaxLotView,
)
from seed.serializers.projects import ProjectSerializer
from seed.serializers.properties import PropertyViewSerializer
from seed.serializers.taxlots import TaxLotViewSerializer
from seed.utils.api import api_endpoint_class, drf_api_endpoint

# missing from DRF
status.HTTP_422_UNPROCESSABLE_ENTITY = 422

_log = logging.getLogger(__name__)

DEFAULT_CUSTOM_COLUMNS = [
    'project_id',
    'project_building_snapshots__status_label__name'
]

COMPLIANCE_KEYS = ['compliance_type', 'end_date', 'deadline_date']

PROJECT_KEYS = ['name', 'description', 'status', 'is_compliance']

COMPLIANCE_LOOKUP = {
    unicode(choice[1]).lower(): choice[0]
    for choice in COMPLIANCE_CHOICES
}

STATUS_LOOKUP = {
    unicode(choice[1]).lower(): choice[0] for choice in STATUS_CHOICES
}

PLURALS = {'property': 'properties', 'taxlot': 'taxlots'}


class ProjectViewSet(DecoratorMixin(drf_api_endpoint),
                     viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    renderer_classes = (JSONRenderer,)
    parser_classes = (JSONParser,)
    authentication_classes = (SessionAuthentication, SEEDAuthentication)
    query_set = Project.objects.none()
    ProjectViewModels = {
        'property': ProjectPropertyView, 'taxlot': ProjectTaxLotView
    }
    ViewModels = {
        'property': PropertyView, 'taxlot': TaxLotView
    }

    # helper methods
    def get_error(self, error, key=None, val=None):
        """Return error message and corresponding http status code."""
        errors = {
            'not found': (
                'Could not find project with {}: {}'.format(key, val),
                status.HTTP_404_NOT_FOUND
            ),
            'permission denied': (
                'Permission denied', status.HTTP_403_FORBIDDEN
            ),
            'bad request': (
                'Incorrect {}'.format(key), status.HTTP_400_BAD_REQUEST
            ),
            'missing param': (
                'Required parameter(s) missing: {}'.format(key),
                status.HTTP_400_BAD_REQUEST
            ),
            'conflict': (
                '{} already exists for {}'.format(key, val),
                status.HTTP_409_CONFLICT
            ),
            'missing inventory': (
                'No {} views found'.format(key),
                status.HTTP_404_NOT_FOUND
            ),
            'missing instance': (
                'Could not find instance of {} with pk {}'.format(key, val),
                status.HTTP_404_NOT_FOUND
            ),
            'misc': (key, status.HTTP_400_BAD_REQUEST)
        }
        return errors[error]

    def get_key(self, pk):
        """Determine where to use slug or pk to identify project."""
        try:
            pk = int(pk)
            key = 'id'
        except ValueError:
            key = 'slug'
        return key

    def get_params(self, keys):
        """
        Get required params from post etc body.

        Returns dict of params and list of missing params.
        """
        rdict = {
            key: self.request.data.get(key) for key in keys
            if self.request.data.get(key, None) is not None
        }
        missing = [key for key in keys if key not in rdict]
        return rdict, missing

    def get_project(self, key, pk):
        """Get project for view."""
        # convert to int if number and look up by pk, otherwise slug
        filter_dict = {key: pk}
        return self.get_queryset().filter(
            **filter_dict
        )

    def get_organization(self):
        """Get org id from query param or request.user."""
        if not getattr(self, '_organization', None):
            try:
                self._organization = self.request.user.orgs.get(
                    pk=self.request.query_params["organization_id"],
                ).pk
            except (KeyError, ObjectDoesNotExist):
                self._organization = self.request.user.orgs.all()[0].pk
        return self._organization

    def get_queryset(self):
        return Project.objects.filter(
            super_organization_id=self.get_organization()
        ).order_by("name").distinct()

    def get_status(self, status):
        """Get status from string or int"""
        try:
            status = int(status)
        except ValueError:
            status = STATUS_LOOKUP[status.lower()]
        return status

    def project_view_factory(self, inventory_type, project_id, view_id):
        """ProjectPropertyView/ProjectTaxLotView factory."""
        Model = self.ProjectViewModels[inventory_type]
        create_dict = {
            'project_id': project_id,
            '{}_view_id'.format(inventory_type): view_id
        }
        return Model(**create_dict)

    # CRUD Views
    @api_endpoint_class
    @has_perm_class('requires_viewer')
    def list(self, request):
        """
        Retrieves all projects for a given organization.

        :GET: Expects organization_id in query string.

        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query

        Returns::

            {
                'status': 'success',
                'projects': [
                    {
                        'id': project's primary key,
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
                        'end_date': Timestamp of end of project,
                        'property_count': number of property views associated with project,
                        'taxlot_count':  number of taxlot views associated with project,
                    }...
                ]
            }
        """
        projects = [
            ProjectSerializer(proj).data for proj in self.get_queryset()
        ]
        status_code = status.HTTP_200_OK
        result = {
            'status': 'success',
            'projects': projects
        }
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_viewer')
    def retrieve(self, request, pk):
        """
        Retrieves details about a project.

        :GET: Expects organization_id in query string.
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: project slug or pk
              description: The project slug identifier or primary key for this project
              required: true
              paramType: path

        Returns::

            {
             'id': project's primary key,
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
             'property_count': number of property views associated with project,
             'taxlot_count':  number of taxlot views associated with project,
             'property_views': [list of serialized property views associated with the project...],
             'taxlot_views': [list of serialized taxlot views associated with the project...],
            }

        """

        error = None
        status_code = status.HTTP_200_OK
        key = self.get_key(pk)
        project = self.get_project(key, pk)
        cycle = request.query_params.get('cycle', None)
        if not project:
            error, status_code = self.get_error(
                'not found', key=key, val=pk
            )
            result = {'status': 'error', 'message': error}
        else:
            project = project[0]
            property_views = project.property_views.all()
            taxlot_views = project.taxlot_views.all()
            if cycle:
                property_views = property_views.filter(
                    cycle_id=cycle
                )
                taxlot_views = taxlot_views.filter(
                    cycle_id=cycle
                )
            project_data = ProjectSerializer(project).data
            project_data['property_views'] = [
                PropertyViewSerializer(property_view).data
                for property_view in property_views
            ]
            project_data['taxlot_views'] = [
                TaxLotViewSerializer(taxlot_view).data
                for taxlot_view in taxlot_views
            ]
            result = {
                'status': 'success',
                'project': project_data,
            }
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def create(self, request):
        """
        Creates a new project

        :POST: Expects organization_id in query string.
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
            - name: is_compliance
              description: add compliance data if true
              type: bool
              required: true
            - name: compliance_type
              description: description of type of compliance
              type: string
              required: true if is_compliance else false
            - name: description
              description: description of new project
              type: string
              required: true if is_compliance else false
            - name: end_date
              description: Timestamp for when project ends
              type: string
              required: true if is_compliance else false
            - name: deadline_date
              description: Timestamp for compliance deadline
              type: string
              required: true if is_compliance else false
        Returns::
            {
                'status': 'success',
                'project': {
                        'id': project's primary key,
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
                        'end_date': Timestamp of end of project,
                        'property_count': 0,
                        'taxlot_count':  0,
                    }
            }
        """
        error = None
        status_code = status.HTTP_200_OK
        super_organization_id = self.get_organization()
        project_data, missing = self.get_params(PROJECT_KEYS)
        project_data.update({
            'owner': request.user,
            'super_organization_id': super_organization_id,
        })
        is_compliance = project_data.pop('is_compliance', None)
        if missing:
            error, status_code = self.get_error(
                'missing param', key=", ".join(missing)
            )
        else:
            try:
                # convert to int equivalent
                project_data['status'] = self.get_status(project_data['status'])
            except KeyError:
                error, status_code = self.get_status(
                    'bad request', key='status'
                )
            if not error and is_compliance:
                compliance_data, missing = self.get_params(
                    COMPLIANCE_KEYS
                )
                if missing:
                    error, status_code = self.get_error(
                        'missing param', key=", ".join(missing)
                    )
                else:
                    compliance_data = convert_dates(
                        compliance_data, ['end_date', 'deadline_date']
                    )
        if not error and Project.objects.filter(
            name=project_data['name'],
            super_organization_id=super_organization_id
        ).exists():
            error, status_code = self.get_error(
                'conflict', key='project', val='organization'
            )
        if not error:
            if Project.objects.filter(
                name=project_data['name'], owner=request.user,
                super_organization_id=super_organization_id,
            ).exists():
                error, status_code = self.get_error(
                    'conflict', key='organization/user'
                )
            else:
                project = Project.objects.create(**project_data)
                if is_compliance:
                    compliance_data['project'] = project
                    Compliance.objects.create(**compliance_data)
        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {
                'status': 'success',
                'project': ProjectSerializer(project).data
            }

        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def destroy(self, request, pk):
        """
        Delete a project.

        :DELETE: Expects organization_id in query string.
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
            - name: project slug or pk
              description: The project slug identifier or primary key for this project
              required: true
              paramType: path

        Returns::
            {
                'status': 'success',
            }
        """
        error = None
        # DRF uses this, but it causes nothing to be returned
        # status_code = status.HTTP_204_NO_CONTENT
        status_code = status.HTTP_200_OK
        organization_id = request.query_params.get('organization_id', None)
        if not organization_id:
            error, status_code = self.get_error(
                'missing param', key='organization_id'
            )
        elif not int(organization_id) == self.get_organization():
            error, status_code = self.get_error(
                'bad request', key='organization_id'
            )

        if not error:
            key = self.get_key(pk)
            project = self.get_project(key, pk)
            if not project:
                error, status_code = self.get_error(
                    'not found', key=key, val=pk
                )
            else:
                project = project[0]
        if not error:
            if project.super_organization_id != int(organization_id):
                error, status_code = self.get_error('permssion denied')
            else:
                ProjectPropertyView.objects.filter(project=project).delete()
                ProjectTaxLotView.objects.filter(project=project).delete()
                project.delete()

        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {'status': 'success'}
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def update(self, request, pk):
        """
        Updates a project

        :PUT: Expects organization_id in query string.
        ---
        parameters:
            - name: organization_id
              description: ID of organization to associate new project with
              type: integer
              required: true
              paramType: query
            - name: project slug or pk
              description: The project slug identifier or primary key for this project
              required: true
              paramType: path
            - name: name
              description: name of the new project
              type: string
              required: true
            - name: is_compliance
              description: add compliance data if true
              type: bool
              required: true
            - name: compliance_type
              description: description of type of compliance
              type: string
              required: true if is_compliance else false
            - name: description
              description: description of new project
              type: string
              required: true if is_compliance else false
            - name: end_date
              description: Timestamp for when project ends
              type: string
              required: true if is_compliance else false
            - name: deadline_date
              description: Timestamp for compliance deadline
              type: string
              required: true if is_compliance else false
        Returns::
            {
                'status': 'success',
                'project': {
                        'id': project's primary key,
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
                        'end_date': Timestamp of end of project,
                        'property_count': number of property views associated with project,
                        'taxlot_count':  number of taxlot views associated with project,
                }
            }
        """
        error = None
        status_code = status.HTTP_200_OK
        project_data, missing = self.get_params(PROJECT_KEYS)
        project_data['last_modified_by'] = request.user
        if missing:
            error, status_code = self.get_error(
                'missing param', key=", ".join(missing)
            )
        else:
            # convert to int equivalent
            project_data['status'] = self.get_status(project_data['status'])
            is_compliance = project_data.pop('is_compliance')
            if is_compliance:
                compliance_data, missing = self.get_params(COMPLIANCE_KEYS)
                compliance_data = convert_dates(
                    compliance_data, ['end_date', 'deadline_date']
                )
            if missing:
                error, status_code = self.get_error(
                    'missing param', key=", ".join(missing)
                )
        if not error:
            key = self.get_key(pk)
            project = self.get_project(key, pk)
            if not project:
                error, status_code = self.get_error(
                    'not found', key=key, val=pk
                )
            else:
                project = project[0]
                compliance = project.get_compliance()
                if is_compliance:
                    if not compliance:
                        compliance = Compliance(project=project)
                    compliance = update_model(
                        compliance, compliance_data
                    )
                project = update_model(project, project_data)
                if is_compliance:
                    compliance.save()
                # delete compliance if one exists
                elif compliance:
                    compliance.delete()
                project.save()
        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {
                'status': 'success',
                'project': ProjectSerializer(project).data
            }
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def partial_update(self, request, pk):
        """
        Updates a project. Allows partial update, i.e. only updated param s need be supplied.

        :PUT: Expects organization_id in query string.
        ---
        parameters:
            - name: organization_id
              description: ID of organization to associate new project with
              type: integer
              required: true
              paramType: query
            - name: project slug or pk
              description: The project slug identifier or primary key for this project
              required: true
              paramType: path
            - name: name
              description: name of the new project
              type: string
              required: false
            - name: is_compliance
              description: add compliance data if true
              type: bool
              required: false
            - name: compliance_type
              description: description of type of compliance
              type: string
              required: true if is_compliance else false
            - name: description
              description: description of new project
              type: string
              required: true if is_compliance else false
            - name: end_date
              description: Timestamp for when project ends
              type: string
              required: true if is_compliance else false
            - name: deadline_date
              description: Timestamp for compliance deadline
              type: string
              required: true if is_compliance else false
        Returns::
            {
                'status': 'success',
                'project': {
                        'id': project's primary key,
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
                        'end_date': Timestamp of end of project,
                        'property_count': number of property views associated with project,
                        'taxlot_count':  number of taxlot views associated with project,
                }
            }
        """
        error = None
        status_code = status.HTTP_200_OK
        project_data, _ = self.get_params(PROJECT_KEYS)
        project_data['last_modified_by'] = request.user
        if 'status' in project_data:
            # convert to int equivalent
            project_data['status'] = self.get_status(project_data['status'])
        is_compliance = project_data.pop('is_compliance', None)
        if is_compliance:
            compliance_data, _ = self.get_params(COMPLIANCE_KEYS)
            compliance_data = convert_dates(
                compliance_data, ['end_date', 'deadline_date']
            )
        key = self.get_key(pk)
        project = self.get_project(key, pk)
        if not project:
            error, status_code = self.get_error(
                'not found', key=key, val=pk
            )
        else:
            project = project[0]
            compliance = project.get_compliance()
            if is_compliance:
                if not compliance:
                    compliance = Compliance(project=project)
                compliance = update_model(
                    compliance, compliance_data
                )
            project = update_model(project, project_data)
            if is_compliance:
                compliance.save()
            # delete compliance if one exists
            elif is_compliance == 'False':
                compliance.delete()
            project.save()
        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {
                'status': 'success',
                'project': ProjectSerializer(project).data
            }
        return Response(result, status=status_code)

    # Action views

    @api_endpoint_class
    @has_perm_class('requires_member')
    def add(self, request, pk):
        """
        Add inventory to project
        :PUT: Expects organization_id in query string.
        ---
        parameters:
            - name: organization_id
              description: ID of organization to associate new project with
              type: integer
              required: true
            - name: inventory_type
              description: type of inventory to add: 'property' or 'taxlot'
              type: string
              required: true
              paramType: query
            - name: project slug or pk
              description: The project slug identifier or primary key for this project
              required: true
              paramType: path
            - name:  selected
              description: ids of property or taxlot views to add
              type: array[int]
              required: true
        Returns:
            {
                'status': 'success',
                'added': [list of property/taxlot view ids added]
            }
        """
        error = None
        inventory = None
        status_code = status.HTTP_200_OK
        inventory_type = request.query_params.get(
            'inventory_type', request.data.get('inventory_type', None)
        )
        if not inventory_type:
            error, status_code = self.get_error(
                'missing param', 'inventory_type'
            )
        else:
            key = self.get_key(pk)
            project = self.get_project(key, pk)
            if not project:
                error, status_code = self.get_error(
                    'not found', key=key, val=pk
                )
        if not error:
            project = project[0]
            view_type = "{}_view".format(inventory_type)
            request.data['inventory_type'] = view_type
            params = search.process_search_params(
                request.data, request.user, is_api_request=False
            )
            organization_id = self.get_organization()
            params['organization_id'] = organization_id
            qs = search.inventory_search_filter_sort(
                view_type, params=params, user=request.user
            )
            if request.data.get('selected', None)\
                    and isinstance(request.data.get('selected'), list):
                inventory = qs.filter(pk__in=request.data.get('selected'))
            # TODO is this still relevant
            elif request.data.get('select_all_checkbox', None):
                inventory = qs

            if not inventory:
                error, status_code = self.get_error(
                    'missing inventory', key=inventory_type
                )
        if error:
            result = {'status': 'error', 'message': error}
        else:
            Model = self.ProjectViewModels[inventory_type]
            new_project_views = [
                self.project_view_factory(inventory_type, project.id, view.id)
                for view in inventory
            ]
            Model.objects.bulk_create(new_project_views)
            added = [view.id for view in inventory]
            project.last_modified_by = request.user
            project.save()
            result = {'status': 'success', 'added': added}
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def remove(self, request, pk):
        """
        Remove inventory from  project
        :PUT: Expects organization_id in query string.
        ---
        parameters:
            - name: organization_id
              description: ID of organization to associate new project with
              type: integer
              required: true
            - name: inventory_type
              description: type of inventory to add: 'property' or 'taxlot'
              type: string
              required: true
              paramType: query
            - name: project slug or pk
              description: The project slug identifier or primary key for this project
              required: true
              paramType: path
            - name:  selected
              description: ids of property or taxlot views to add
              type: array[int]
              required: true
        Returns:
            {
                'status': 'success',
                'removed': [list of property/taxlot view ids removed]
            }
        """
        error = None
        status_code = status.HTTP_200_OK
        inventory_type = request.query_params.get(
            'inventory_type', request.data.get('inventory_type', None)
        )
        selected = request.data.get('selected', None)
        missing = []
        if not inventory_type:
            missing.append('inventory_type')
        if selected is None:
            missing.append('selected')
        if missing:
            error, status_code = self.get_error(
                'missing param', ",".join(missing)
            )
        else:
            key = self.get_key(pk)
            project = self.get_project(key, pk)
            if not project:
                error, status_code = self.get_error(
                    'not found', key=key, val=pk
                )
        if not error:
            project = project[0]
            ViewModel = self.ViewModels[inventory_type]
            if selected:
                filter_dict = {
                    'id__in': request.data.get(
                        'selected'
                    )
                }
            elif selected == []:
                super_organization_id = self.get_organization()
                filter_dict = {
                    "state__super_organization_id": super_organization_id
                }
                for key in [inventory_type, 'cycle', 'state']:
                    val = request.data.get(key, None)
                    if val:
                        if isinstance(val, list):
                            filter_dict['{}_id__in'.format(key)] = val
                        else:
                            filter_dict['{}_id'.format(key)] = val
            views = ViewModel.objects.filter(**filter_dict).values_list('id')
            if not views:
                error, status_code = self.get_error(
                    'missing inventory', key=inventory_type
                )
            else:
                Model = self.ProjectViewModels[inventory_type]
                filter_dict = {
                    "project_id": project.pk,
                    "{}_view__in".format(inventory_type): views
                }
                project_views = Model.objects.filter(**filter_dict)
                removed = [view.pk for view in project_views]
                project_views.delete()
                project.last_modified_by = request.user
                project.save()
        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {'status': 'success', 'removed': removed}
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_viewer')
    @list_route(methods=['GET'])
    def count(self, request):
        """
        Returns the number of projects within the org tree to which
        a user belongs.  Counts projects in parent orgs and sibling orgs.

        :GET: Expects organization_id in query string.
        ---
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              paramType: query
        type:
            status:
                type: string
                description: success, or error
            count:
                type: integer
                description: number of projects
        """
        status_code = status.HTTP_200_OK
        super_organization_id = self.get_organization()
        count = Project.objects.filter(
            super_organization_id=super_organization_id
        ).distinct().count()
        result = {'status': 'success', 'count': count}
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def update_details(self, request, pk):
        """
        Updates extra information about the inventory/project relationship.
        In particular, whether the property/taxlot  is compliant
        and who approved it.

        :PUT: Expects organization_id in query string.
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              type: integer
              paramType: query
            - name: inventory_type
              description: type of inventory to add: 'property' or 'taxlot'
              required: true
              type: string
              paramType: query
            - name: id
              description: id of property/taxlot  view to update
              required: true
              type: integer
              paramType: string
            - name: compliant
              description: is compliant
              required: true
              type: bool
              paramType: string

        Returns::
            {
                 'status': 'success',
                 'approved_date': Timestamp of change (now),
                 'approver': Email address of user making change
            }
        """
        error = None
        status_code = status.HTTP_200_OK
        params, missing = self.get_params(
            ['id', 'compliant']
        )
        inventory_type = request.query_params.get(
            'inventory_type', request.data.get('inventory_type', None)
        )
        if not inventory_type:
            missing.append('inventory_type')
        if missing:
            error, status_code = self.get_error(
                'missing param', key=", ".join(missing)
            )
        else:
            if not isinstance(params['compliant'], bool):
                error, status_code = self.get_error(
                    'misc', key='compliant must be of type bool',
                )
        if not error:
            key = self.get_key(pk)
            project = self.get_project(key, pk)
            if not project:
                error, status_code = self.get_error(
                    'not found', key=key, val=pk
                )
        if not error:
            project = project[0]
            Model = self.ProjectViewModels[inventory_type]
            filter_dict = {
                "project_id": project.id,
                "{}_view_id".format(inventory_type): params['id']
            }
            try:
                view = Model.objects.get(**filter_dict)
            except Model.DoesNotExist:
                error, status_code = self.get_error(
                    'missing inventory', key=inventory_type
                )
        if not error:
            view.approved_date = timezone.now()
            view.approver = request.user
            view.compliant = params['compliant']
            view.save()
        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {
                'status': 'success',
                'approved_date': view.approved_date.strftime("%m/%d/%Y"),
                'approver': view.approver.email,
            }
        return Response(result, status=status_code)

    @api_endpoint_class
    @has_perm_class('requires_member')
    def transfer(self, request, pk, action):
        """
        Move or copy inventory from one project to another

        :PUT: Expects organization_id in query string.
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: The organization_id for this user's organization
              required: true
              type: integer
              paramType: query
            - name: inventory_type
              description: type of inventory to add: 'property' or 'taxlot'
              required: true
              type: string
              paramType: query
            - name: copy or move
              description: Whether to move or copy inventory
              required: true
              paramType: path
              required: true
            -name: target
              type: string or int
              description: target project slug/id  to move/copy to.
              required: true
            - name: selected
              description: JSON array, list of property/taxlot views to be transferred
              paramType: array[int]
              required: true
        """
        error = None
        status_code = status.HTTP_200_OK
        params, missing = self.get_params(
            ['selected', 'target']
        )
        inventory_type = request.query_params.get(
            'inventory_type', request.data.get('inventory_type', None)
        )
        if not inventory_type:
            missing.append('inventory_type')
        if missing:
            error, status_code = self.get_error(
                'missing param', key=", ".join(missing)
            )
        else:
            key = self.get_key(pk)
            project = self.get_project(key, pk)
            if not project:
                error, status_code = self.get_error(
                    'not found', key=key, val=pk
                )
            else:
                target_key = self.get_key(params['target'])
                target = self.get_project(target_key, params['target'])
                if not target:
                    error, status_code = self.get_error(
                        'not found', key=target_key, val=params['target']
                    )
                    error += 'for target'

        if not error:
            project = project[0]
            target = target[0]
            ProjectViewModel = self.ProjectViewModels[inventory_type]
            filter_dict = {
                "{}_view_id__in".format(inventory_type):
                params['selected'],
                'project_id': project.id
            }
            old_project_views = ProjectViewModel.objects.filter(
                **filter_dict
            )

            if action == 'copy':
                new_project_views = []
                # set pk to None to create a copy of the django instance
                for view in old_project_views:
                    view.pk = None
                    view.project = target
                    new_project_views.append(view)
                try:
                    ProjectViewModel.objects.bulk_create(
                        new_project_views
                    )
                except IntegrityError:
                    error, status_code = self.get_error(
                        'conflict',
                        key="One or more {}".format(
                            PLURALS[inventory_type]
                        ),
                        val='target project'
                    )

            else:
                try:
                    old_project_views.update(project=target)

                except IntegrityError:
                    error, status_code = self.get_error(
                        'conflict',
                        key="One or more {}".format(
                            PLURALS[inventory_type]
                        ),
                        val='target project'
                    )
        if error:
            result = {'status': 'error', 'message': error}
        else:
            result = {'status': 'success'}
        return Response(result, status=status_code)


def convert_dates(data, keys):
    updated = {key: parser.parse(data[key]) for key in keys if key in data}
    data.update(updated)
    return data


def update_model(model, data):
    for key, val in data.items():
        setattr(model, key, val)
    return model
