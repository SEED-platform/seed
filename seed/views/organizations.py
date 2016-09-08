# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging

from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser,
)
from seed.models import CanonicalBuilding
from seed.landing.models import SEEDUser as User
from seed.utils.organizations import create_organization
from rest_framework.authentication import SessionAuthentication
from seed.authentication import SEEDAuthentication
from django.http import JsonResponse
from rest_framework import viewsets
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import api_endpoint_class
from rest_framework.decorators import detail_route
from django.core.exceptions import ObjectDoesNotExist
from seed.public.models import INTERNAL, PUBLIC, SharedBuildingField
from seed.utils.buildings import get_columns as utils_get_columns
from seed.cleansing.models import (
    CATEGORY_MISSING_MATCHING_FIELD,
    CATEGORY_MISSING_VALUES,
    CATEGORY_IN_RANGE_CHECKING,
    DATA_TYPES as CLEANSING_DATA_TYPES,
    SEVERITY as CLEANSING_SEVERITY,
    Rules
)
from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.decorators import get_prog_key
from seed import tasks

def _dict_org(request, organizations):
    """returns a dictionary of an organization's data."""

    cbs = list(CanonicalBuilding.objects.filter(canonical_snapshot__super_organization__in=organizations).values('canonical_snapshot__super_organization_id'))

    org_map = dict((x.pk, 0) for x in organizations)
    for cb in cbs:
        org_id = cb['canonical_snapshot__super_organization_id']
        org_map[org_id] = org_map[org_id] + 1

    orgs = []
    for o in organizations:
        # We don't wish to double count sub organization memberships.
        org_users = OrganizationUser.objects.select_related('user') \
            .filter(organization=o)

        owners = []
        role_level = None
        user_is_owner = False
        for ou in org_users:
            if ou.role_level == ROLE_OWNER:
                owners.append({
                    'first_name': ou.user.first_name,
                    'last_name': ou.user.last_name,
                    'email': ou.user.email,
                    'id': ou.user_id
                })

                if ou.user == request.user:
                    user_is_owner = True

            if ou.user == request.user:
                role_level = _get_js_role(ou.role_level)

        org = {
            'name': o.name,
            'org_id': o.pk,
            'id': o.pk,
            'number_of_users': len(org_users),
            'user_is_owner': user_is_owner,
            'user_role': role_level,
            'owners': owners,
            'sub_orgs': _dict_org(request, o.child_orgs.all()),
            'is_parent': o.is_parent,
            'parent_id': o.parent_id,
            'num_buildings': org_map[o.pk],
            'created': o.created.strftime('%Y-%m-%d') if o.created else '',
        }
        orgs.append(org)

    return orgs


def _get_js_role(role):
    """return the JS friendly role name for user

    :param role: role as defined in superperms.models
    :returns: (string) JS role name
    """
    roles = {
        ROLE_OWNER: 'owner',
        ROLE_VIEWER: 'viewer',
        ROLE_MEMBER: 'member',
    }
    return roles.get(role, 'viewer')


def _get_role_from_js(role):
    """return the OrganizationUser role_level from the JS friendly role name

    :param role: 'member', 'owner', or 'viewer'
    :returns: int role as defined in superperms.models
    """
    roles = {
        'owner': ROLE_OWNER,
        'viewer': ROLE_VIEWER,
        'member': ROLE_MEMBER,
    }
    return roles[role]


def _get_js_rule_type(data_type):
    """return the JS friendly data type name for the data cleansing rule

    :param data_type: data cleansing rule data type as defined in cleansing.models
    :returns: (string) JS data type name
    """
    return dict(CLEANSING_DATA_TYPES).get(data_type)


def _get_rule_type_from_js(data_type):
    """return the Rules TYPE from the JS friendly data type

    :param data_type: 'string', 'number', 'date', or 'year'
    :returns: int data type as defined in cleansing.models
    """
    d = {v: k for k, v in dict(CLEANSING_DATA_TYPES).items()}
    return d.get(data_type)


def _get_js_rule_severity(severity):
    """return the JS friendly severity name for the data cleansing rule

    :param severity: data cleansing rule severity as defined in cleansing.models
    :returns: (string) JS severity name
    """
    return dict(CLEANSING_SEVERITY).get(severity)


def _get_severity_from_js(severity):
    """return the Rules SEVERITY from the JS friendly severity

    :param severity: 'error', or 'warning'
    :returns: int severity as defined in cleansing.models
    """
    d = {v: k for k, v in dict(CLEANSING_SEVERITY).items()}
    return d.get(severity)


def _save_fields(org, new_fields, old_fields, is_public=False):
    """Save Building to be Shared."""
    old_fields_names = set(old_fields.values_list('field__name', flat=True))
    new_fields_names = set([f['sort_column'] for f in new_fields])
    field_type = PUBLIC if is_public else INTERNAL

    # remove the fields that weren't posted
    to_remove = old_fields_names - new_fields_names
    SharedBuildingField.objects.filter(
        field__name__in=to_remove, field_type=field_type
    ).delete()

    # add new fields that were posted to the db
    # but only the new ones
    to_add = new_fields_names - old_fields_names
    for new_field_name in to_add:
        # All Exported Fields are stored within superperms.
        exported_field, created = org.exportable_fields.get_or_create(
            name=new_field_name, field_model='BuildingSnapshot'
        )
        # The granular visibility settings are stored in the 'public' app.
        SharedBuildingField.objects.create(
            org=org, field=exported_field, field_type=field_type
        )


_log = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ViewSet):
    raise_exception = True
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

    @api_endpoint_class
    @ajax_request_class
    def list(self, request):
        """
        Retrieves all orgs the user has access to.

        Returns::

            {'organizations': [
                {'name': org name,
                 'org_id': org's identifier (used with Authorization header),
                 'id': org's identifier,
                 'number_of_users': count of members of org,
                 'user_is_owner': True if the user is owner of this org,
                 'user_role': The role of user in this org (owner, viewer, member),
                 'owners': [
                             {
                              'first_name': the owner's first name,
                              'last_name': the owner's last name,
                              'email': the owner's email address,
                              'id': the owner's identifier (int)
                             }
                           ]
                 'sub_orgs': [ a list of orgs having this org as parent, in
                            the same format...],
                 'is_parent': True if this org contains suborgs,
                 'parent_id': id of this orgs parent (self.id if it is a parent)
                 'num_buildings': Count of buildings belonging to this org
                }...
               ]
            }
        """
        if request.user.is_superuser:
            qs = Organization.objects.all()
        else:
            qs = request.user.orgs.all()

        return JsonResponse({'organizations': _dict_org(request, qs)})

    # @permission_required('seed.can_access_admin')
    @api_endpoint_class
    @ajax_request_class
    def destroy(self, request, pk=None):
        """
        Starts a background task to delete an organization and all related data.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              type: integer
              description: Organization ID (primary key)
              required: true
              paramType: path
        type:
            status:
                description: success or error
                type: string
                required: true
            progress_key:
                description: ID of background job, for retrieving job progress
                type: string
                required: true
        """
        org_id = pk
        deleting_cache_key = get_prog_key(
            'delete_organization_buildings',
            org_id
        )
        tasks.delete_organization.delay(org_id, deleting_cache_key)
        return JsonResponse({
            'status': 'success',
            'progress': 0,
            'progress_key': deleting_cache_key
        })

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, pk=None):
        """
        Retrieves a single organization by id.
        ---

        Returns::

            {'status': 'success or error', 'message': 'error message, if any',
             'organization':
                {'name': org name,
                 'org_id': org's identifier (used with Authorization header),
                 'id': org's identifier,
                 'number_of_users': count of members of org,
                 'user_is_owner': True if the user is owner of this org,
                 'user_role': The role of user in this org (owner, viewer, member),
                 'owners': [
                     {
                      'first_name': the owner's first name,
                      'last_name': the owner's last name,
                      'email': the owner's email address,
                      'id': the owner's identifier (int)
                      }
                     ]
                  'sub_orgs': [ a list of orgs having this org as parent, in
                                the same format...],
                  'is_parent': True if this org contains suborgs,
                  'num_buildings': Count of buildings belonging to this org
                }
            }
        """
        org_id = pk

        if org_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'no organization_id sent'
            }, status=400)

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization does not exist'
            }, status=404)
        if (
            not request.user.is_superuser and
            not OrganizationUser.objects.filter(
                user=request.user,
                organization=org,
                role_level__in=[ROLE_OWNER, ROLE_MEMBER, ROLE_VIEWER]
            ).exists()
        ):
            # TODO: better permission and return 401 or 403
            return JsonResponse({
                'status': 'error',
                'message': 'user is not the owner of the org'
            }, status=403)

        return JsonResponse({
            'status': 'success',
            'organization': _dict_org(request, [org])[0],
        })

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @detail_route(methods=['GET'])
    def users(self, request, pk=None):
        """
        Retrieve all users belonging to an org.

        Payload::

            {'organization_id': org_id}

        Returns::

            {'status': 'success',
             'users': [
                {
                 'first_name': the user's first name,
                 'last_name': the user's last name,
                 'email': the user's email address,
                 'id': the user's identifier (int),
                 'role': the user's role ('owner', 'member', 'viewer')
                }
              ]
            }

        .. todo::

            check permissions that request.user is owner or admin
            and get more info about the users.
        """

        try:
            org = Organization.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at pk = ' + str(pk)},
                                status=404)
        users = []
        for u in org.organizationuser_set.all():
            user = u.user
            users.append({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_id': user.pk,
                'role': _get_js_role(u.role_level)
            })

        return JsonResponse({'status': 'success', 'users': users})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @detail_route(methods=['DELETE'])
    def remove_user(self, request, pk=None):
        """
        Removes a user from an organization.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: user_id
              description: User ID (Primary key) of the user to remove from the organization
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: info/error message, if any
                required: false
        """
        body = request.data

        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization does not exist'
            }, status=404)

        if body.get('user_id') is None:
            return JsonResponse({
                'status': 'error',
                'message': 'missing the user_id'
            }, status=400)

        try:
            user = User.objects.get(pk=body['user_id'])
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'user does not exist'
            }, status=404)

        if not OrganizationUser.objects.filter(
            user=request.user, organization=org, role_level=ROLE_OWNER
        ).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'only the organization owner can remove a member'
            }, status=403)

        is_last_member = not OrganizationUser.objects.filter(
            organization=org,
        ).exclude(user=user).exists()

        if is_last_member:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one member'
            }, status=409)

        is_last_owner = not OrganizationUser.objects.filter(
            organization=org,
            role_level=ROLE_OWNER,
        ).exclude(user=user).exists()

        if is_last_owner:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one owner level member'
            }, status=409)

        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.delete()

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    def create(self, request):
        """
        Creates a new organization.
        ---
        parameters:
            - name: organization_name
              description: The new organization name
              type: string
              required: true
            - name: user_id
              description: The user ID (primary key) to be used as the owner of the new organization
              type: integer
              required: true
        type:
           status:
               type: string
               description: success or error
               required: true
           message:
               type: string
               description: error/informational message, if any
               required: false
           organization_id:
               type: string
               description: The ID of the new org, if created
               required: false
        """
        body = request.data
        user = User.objects.get(pk=body['user_id'])
        org_name = body['organization_name']

        if Organization.objects.filter(name=org_name).exists():
            return JsonResponse({
                'status': 'error',
                'message': 'organization name already exists'
            }, status=409)

        org, _, _ = create_organization(user, org_name, org_name)
        return JsonResponse({'status': 'success',
                             'message': 'organization created',
                             'organization_id': org.pk})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @detail_route(methods=['PUT'])
    def add_user(self, request, pk=None):
        """
        Adds an existing user to an organization.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: user_id
              description: User ID (Primary key) of the user to add to the organization
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: info/error message, if any
                required: false
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        user = User.objects.get(pk=body['user_id'])

        org.add_member(user)

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @detail_route(methods=['PUT'])
    def save_settings(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields

        Payload::

            {
                'organization_id: 2,
                'organization': {
                    'query_threshold': 2,
                    'name': 'demo org',
                    'fields': [  # All internal sibling org shared fields
                        {
                            'sort_column': database/search field name,
                                e.g. 'pm_property_id',
                        }
                    ],
                    'public_fields': [  # All publicly shared fields
                        {
                            'sort_column': database/search field name,
                                e.g. 'pm_property_id',
                        }
                    ],
                }
            }

        Returns::

            {
                'status': 'success or error',
                'message': 'error message, if any'
            }
        """
        body = json.loads(request.body)
        org = Organization.objects.get(pk=pk)
        posted_org = body.get('organization', None)
        if posted_org is None:
            return JsonResponse({'status': 'error', 'message': 'malformed request'}, status=400)

        desired_threshold = posted_org.get('query_threshold', None)
        if desired_threshold is not None:
            org.query_threshold = desired_threshold

        desired_name = posted_org.get('name', None)
        if desired_name is not None:
            org.name = desired_name
        org.save()

        # Update the selected exportable fields.
        new_fields = posted_org.get('fields', None)
        new_pub_fields = posted_org.get('public_fields', None)
        if new_fields is not None:
            old_fields = SharedBuildingField.objects.filter(
                org=org, field_type=INTERNAL
            ).select_related('field')

            _save_fields(org, new_fields, old_fields)

        if new_pub_fields is not None:
            old_pub_fields = SharedBuildingField.objects.filter(
                org=org, field_type=PUBLIC
            ).select_related('field')

            _save_fields(org, new_pub_fields, old_pub_fields, is_public=True)

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def query_threshold(self, request, pk=None):
        """
        Returns the "query_threshold" for an org.  Searches from
        members of sibling orgs must return at least this many buildings
        from orgs they do not belong to, or else buildings from orgs they
        don't belong to will be removed from the results.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
        type:
            status:
                type: string
                required: true
                description: success or error
            query_threshold:
                type: integer
                required: true
                description: Minimum number of buildings that must be returned from a search to avoid
                             squelching non-member-org results
        """
        org = Organization.objects.get(pk=pk)
        return JsonResponse({
            'status': 'success',
            'query_threshold': org.query_threshold
        })

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['GET'])
    def shared_fields(self, request, pk=None):
        """
        Retrieves all fields marked as shared for this org tree.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
        type: object
        """
        """
            {
             'status': 'success',
             'shared_fields': [
                 {
                  "title": Display name of field,
                  "sort_column": database/search name of field,
                  "class": css used for field,
                  "title_class": css used for title,
                  "type": data type of field,
                      (One of: 'date', 'floor_area', 'link', 'string', 'number')
                  "field_type": classification of field.  One of:
                      'contact_information', 'building_information',
                      'assessor', 'pm',
                  "sortable": True if buildings can be sorted on this field,
                 }
                 ...
               ],
               'public_fields': [
                   {
                      "title": Display name of field,
                      "sort_column": database/search name of field,
                      "class": css used for field,
                      "title_class": css used for title,
                      "type": data type of field,
                        (One of: 'date', 'floor_area', 'link', 'string', 'number')
                      "field_type": classification of field.  One of:
                          'contact_information', 'building_information',
                          'assessor', 'pm',
                      "sortable": True if buildings can be sorted on this field,
                     }
                     ...
               ]
            }

        """
        org_id = pk
        org = Organization.objects.get(pk=org_id)

        result = {'status': 'success',
                  'shared_fields': [],
                  'public_fields': []}
        columns = utils_get_columns(org_id, True)['fields']
        columns = {
            field['sort_column']: field for field in columns
        }

        for exportable_field in SharedBuildingField.objects.filter(
            org=org, field_type=INTERNAL
        ).select_related('field'):
            field_name = exportable_field.field.name
            shared_field = columns[field_name]
            result['shared_fields'].append(shared_field)
        for exportable_field in SharedBuildingField.objects.filter(
            org=org, field_type=PUBLIC
        ).select_related('field'):
            field_name = exportable_field.field.name
            shared_field = columns[field_name]
            result['public_fields'].append(shared_field)

        return JsonResponse(result)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @detail_route(methods=['GET'])
    def cleansing_rules(self, request, pk=None):
        """
        Returns the cleansing rules for an org.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
        type:
            status:
                type: string
                required: true
                description: success or error
            in_range_checking:
                type: array[string]
                required: true
                description: An array of in-range error rules
            missing_matching_field:
                type: array[string]
                required: true
                description: An array of fields to verify existence
            missing_values:
                type: array[string]
                required: true
                description: An array of fields to ignore missing values
        """
        org = Organization.objects.get(pk=pk)

        result = {
            'status': 'success',
            'missing_matching_field': [],
            'missing_values': [],
            'in_range_checking': [],
            # 'data_type_check': []
        }

        rules = Rules.objects.filter(org=org).order_by('field', 'severity')
        if not rules.exists():
            Rules.initialize_rules(org)

        for rule in rules:
            if rule.category == CATEGORY_MISSING_MATCHING_FIELD:
                result['missing_matching_field'].append({
                    'field': rule.field,
                    'severity': _get_js_rule_severity(rule.severity),
                })
            elif rule.category == CATEGORY_MISSING_VALUES:
                result['missing_values'].append({
                    'field': rule.field,
                    'severity': _get_js_rule_severity(rule.severity),
                })
            elif rule.category == CATEGORY_IN_RANGE_CHECKING:
                result['in_range_checking'].append({
                    'field': rule.field,
                    'enabled': rule.enabled,
                    'type': _get_js_rule_type(rule.type),
                    'min': rule.min,
                    'max': rule.max,
                    'severity': _get_js_rule_severity(rule.severity),
                    'units': rule.units
                })
            # elif rule.category == CATEGORY_DATA_TYPE_CHECK:
            #     result['data_type_check'].append({
            #         'field': rule.field
            #     })

        return JsonResponse(result)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @detail_route(methods=['PUT'])
    def reset_cleansing_rules(self, request, pk=None):
        """
        Resets an organization's data cleansing rules
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
        type:
            status:
                type: string
                description: success or error
                required: true
            in_range_checking:
                type: array[string]
                required: true
                description: An array of in-range error rules
            missing_matching_field:
                type: array[string]
                required: true
                description: An array of fields to verify existence
            missing_values:
                type: array[string]
                required: true
                description: An array of fields to ignore missing values
        """
        org = Organization.objects.get(pk=pk)

        Rules.restore_defaults(org)
        return self.get_cleansing_rules(request, pk)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @detail_route(methods=['PUT'])
    def save_cleansing_rules(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields
        Body type is:
        {
            'cleansing_rules': {
                'missing_matching_field': [
                    {
                        'field': 'address_line_1',
                        'severity': 'error'
                    }
                ],
                'missing_values': [
                    {
                        'field': 'address_line_1',
                        'severity': 'error'
                    }
                ],
                'in_range_checking': [
                    {
                        'field': 'conditioned_floor_area',
                        'enabled': true,
                        'type': 'number',
                        'min': null,
                        'max': 7000000,
                        'severity': 'error',
                        'units': 'square feet'
                    },
                ]
            }
        }
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: body
              description: body containing all the things
              type: object
              paramType: body
              required: true
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: error message, if any
                required: true
        """
        body = request.data
        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization does not exist'
            }, status=404)
        if body.get('cleansing_rules') is None:
            return JsonResponse({
                'status': 'error',
                'message': 'missing the cleansing_rules'
            }, status=400)

        posted_rules = body['cleansing_rules']
        updated_rules = []
        for rule in posted_rules['missing_matching_field']:
            updated_rules.append(Rules(
                org=org,
                field=rule['field'],
                category=CATEGORY_MISSING_MATCHING_FIELD,
                severity=_get_severity_from_js(rule['severity'])
            ))
        for rule in posted_rules['missing_values']:
            updated_rules.append(Rules(
                org=org,
                field=rule['field'],
                category=CATEGORY_MISSING_VALUES,
                severity=_get_severity_from_js(rule['severity'])
            ))
        for rule in posted_rules['in_range_checking']:
            updated_rules.append(Rules(
                org=org,
                field=rule['field'],
                enabled=rule['enabled'],
                category=CATEGORY_IN_RANGE_CHECKING,
                type=_get_rule_type_from_js(rule['type']),
                min=rule['min'],
                max=rule['max'],
                severity=_get_severity_from_js(rule['severity']),
                units=rule['units']
            ))

        Rules.delete_rules(org)
        for rule in updated_rules:
            rule.save()
        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @detail_route(methods=['POST'])
    def sub_org(self, request, pk=None):
        """
        Creates a child org of a parent org.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Organization ID (Primary key)
              type: integer
              required: true
              paramType: path
            - name: sub_org_name
              description: Name of the new sub organization
              type: string
              required: true
            - name: sub_org_owner_email
              description: Email of the owner of the sub organization, which must already exist
              type: string
              required: true
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: error message, if any
                required: true
            organization_id:
                type: integer
                description: ID of newly-created org
                required: true
        """
        body = request.data
        org = Organization.objects.get(pk=pk)
        email = body['sub_org_owner_email']
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'User with email address (%s) does not exist' % email
            }, status=404)
        sub_org = Organization.objects.create(
            name=body['sub_org_name']
        )

        OrganizationUser.objects.get_or_create(user=user, organization=sub_org)

        sub_org.parent_org = org

        try:
            sub_org.save()
        except TooManyNestedOrgs:
            sub_org.delete()
            return JsonResponse({
                'status': 'error',
                'message': 'Tried to create child of a child organization.'
            }, status=409)

        return JsonResponse({'status': 'success',
                'organization_id': sub_org.pk})

#
# @ajax_request
# def search_public_fields(request):
#     """Search across all public fields.
#
#     Payload::
#
#         {
#              'q': a string to search on (optional),
#              'show_shared_buildings': True to include buildings from other
#                  orgs in this user's org tree,
#              'order_by': which field to order by (e.g. pm_property_id),
#              'import_file_id': ID of an import to limit search to,
#              'filter_params': { a hash of Django-like filter parameters to limit
#                  query.  See seed.search.filter_other_params.  If 'project__slug'
#                  is included and set to a project's slug, buildings will include
#                  associated labels for that project.
#                }
#              'page': Which page of results to retrieve (default: 1),
#              'number_per_page': Number of buildings to retrieve per page
#                                 (default: 10),
#         }
#
#     Returns::
#
#         {
#              'status': 'success',
#              'buildings': [
#               { all fields for buildings the request user has access to;
#                 e.g.:
#                'canonical_building': the CanonicalBuilding ID of the building,
#                'pm_property_id': ID of building (from Portfolio Manager),
#                'address_line_1': First line of building's address,
#                'property_name': Building's name, if any
#                 ...
#                }...
#               ]
#              'number_matching_search': Total number of buildings matching search,
#              'number_returned': Number of buildings returned for this page
#         }
#     """
#     from seed.views.main import _search_buildings
#     _search_buildings(request)


