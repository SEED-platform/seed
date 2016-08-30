# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_perm, PERMS
from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser,
)
from seed.models import CanonicalBuilding
from seed.landing.models import SEEDUser as User
from seed.tasks import (
    invite_to_seed,
)
from seed.utils.api import api_endpoint
from seed.utils.organizations import create_organization
from seed.cleansing.models import (
    CATEGORY_MISSING_MATCHING_FIELD,
    CATEGORY_MISSING_VALUES,
    CATEGORY_IN_RANGE_CHECKING,
    DATA_TYPES as CLEANSING_DATA_TYPES,
    SEVERITY as CLEANSING_SEVERITY,
    Rules
)


_log = logging.getLogger(__name__)

#
# def _dict_org(request, organizations):
#     """returns a dictionary of an organization's data."""
#
#     cbs = list(CanonicalBuilding.objects.filter(canonical_snapshot__super_organization__in=organizations).values('canonical_snapshot__super_organization_id'))
#
#     org_map = dict((x.pk, 0) for x in organizations)
#     for cb in cbs:
#         org_id = cb['canonical_snapshot__super_organization_id']
#         org_map[org_id] = org_map[org_id] + 1
#
#     orgs = []
#     for o in organizations:
#         # We don't wish to double count sub organization memberships.
#         org_users = OrganizationUser.objects.select_related('user') \
#             .filter(organization=o)
#
#         owners = []
#         role_level = None
#         user_is_owner = False
#         for ou in org_users:
#             if ou.role_level == ROLE_OWNER:
#                 owners.append({
#                     'first_name': ou.user.first_name,
#                     'last_name': ou.user.last_name,
#                     'email': ou.user.email,
#                     'id': ou.user_id
#                 })
#
#                 if ou.user == request.user:
#                     user_is_owner = True
#
#             if ou.user == request.user:
#                 role_level = _get_js_role(ou.role_level)
#
#         org = {
#             'name': o.name,
#             'org_id': o.pk,
#             'id': o.pk,
#             'number_of_users': len(org_users),
#             'user_is_owner': user_is_owner,
#             'user_role': role_level,
#             'owners': owners,
#             'sub_orgs': _dict_org(request, o.child_orgs.all()),
#             'is_parent': o.is_parent,
#             'parent_id': o.parent_id,
#             'num_buildings': org_map[o.pk],
#             'created': o.created.strftime('%Y-%m-%d') if o.created else '',
#         }
#         orgs.append(org)
#
#     return orgs
#
#


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


from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from rest_framework import viewsets
from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import api_endpoint_class
from rest_framework.decorators import list_route, detail_route
from django.core.exceptions import ObjectDoesNotExist


class UserViewSet(LoginRequiredMixin, viewsets.ViewSet):
    raise_exception = True

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    def create(self, request):
        """
        Creates a new SEED user.  One of 'organization_id' or 'org_name' is needed.
        Sends invitation email to the new user.
        ---
        parameters:
            - name: organization_id
              description: Organization ID if adding user to an existing organization
              required: false
              type: integer
            - name: org_name
              description: New organization name if creating a new organization for this user
              required: false
              type: string
            - name: first_name
              description: First name of new user
              required: true
              type: string
            - name: last_name
              description: Last name of new user
              required: true
              type: string
            - name: role
              description: one of owner, member, or viewer
              required: true
              type: string
            - name: email
              description: Email address of the new user
              required: true
              type: string
        type:
            status:
                description: success or error
                required: true
                type: string
            message:
                description: email address of new user
                required: true
                type: string
            org:
                description: name of the new org (or existing org)
                required: true
                type: string
            org_created:
                description: True if new org created
                required: true
                type: string
            username:
                description: Username of new user
                required: true
                type: string
        """
        body = request.data
        org_name = body.get('org_name')
        org_id = body.get('organization_id')
        if ((org_name and org_id) or (not org_name and not org_id)):
            return JsonResponse({
                'status': 'error',
                'message': 'Choose either an existing org or provide a new one'
            }, status=409)

        first_name = body['first_name']
        last_name = body['last_name']
        email = body['email']
        username = body['email']
        user, created = User.objects.get_or_create(username=username.lower())

        if org_id:
            org = Organization.objects.get(pk=org_id)
            org_created = False
        else:
            org, _, _ = create_organization(user, org_name)
            org_created = True

        # Add the user to the org.  If this is the org's first user,
        # the user becomes the owner/admin automatically.
        # see Organization.add_member()
        if not org.is_member(user):
            org.add_member(user)
        if body.get('role'):
            OrganizationUser.objects.filter(
                organization_id=org.pk,
                user_id=user.pk
            ).update(role_level=_get_role_from_js(body['role']))

        if created:
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
        user.save()
        try:
            domain = request.get_host()
        except Exception:
            domain = 'buildingenergy.com'
        invite_to_seed(domain, user.email,
                       default_token_generator.make_token(user), user.pk,
                       first_name)

        return JsonResponse({'status': 'success', 'message': user.email, 'org': org.name,
                'org_created': org_created, 'username': user.username})

    @ajax_request_class
    @has_perm_class('requires_superuser')
    def list(self, request):
        """
        Retrieves all users' email addresses and IDs.
        Only usable by superusers.

        Returns::

            {
                'users': [
                    'email': 'Email address of user',
                    'user_id': 'ID of user'
                ] ...
            }
        """
        users = []
        for u in User.objects.all():
            users.append({'email': u.email, 'user_id': u.pk})

        return JsonResponse({'users': users})

    @ajax_request_class
    @api_endpoint_class
    @list_route(methods=['GET'])
    def my_pk(self, request):
        return JsonResponse({'pk': request.user.id})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @detail_route(methods=['PUT'])
    def update_role(self, request, pk=None):
        """
        Updates a user's role within an organization.
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: ID for the user to modify
              type: integer
              required: true
              paramType: path
            - name: organization_id
              description: The organization ID to update this user within
              type: integer
              required: true
            - name: role
              description: one of owner, member, or viewer
              type: string
              required: true
        type:
            status:
                required: true
                description: success or error
                type: string
            message:
                required: false
                description: error message, if any
                type: string
        """
        body = request.data
        role = _get_role_from_js(body['role'])

        user_id = pk

        organization_id = body['organization_id']

        is_last_member = not OrganizationUser.objects.filter(
            organization=organization_id,
        ).exclude(user=user_id).exists()

        if is_last_member:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one member'
            }, status=409)

        is_last_owner = not OrganizationUser.objects.filter(
            organization=organization_id,
            role_level=ROLE_OWNER,
        ).exclude(user=user_id).exists()

        if is_last_owner:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one owner level member'
            }, status=409)

        OrganizationUser.objects.filter(
            user_id=user_id,
            organization_id=body['organization_id']
        ).update(role_level=role)

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk=None):
        """
        Retrieves the request's user's first_name, last_name, email
        and api key if exists.

        Returns::

            {
                'status': 'success',
                'user': {
                    'first_name': user's first name,
                    'last_name': user's last name,
                    'email': user's email,
                    'api_key': user's API key
                }
            }
        """
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)}, status=403)
        return JsonResponse({
            'status': 'success',
            'user': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'api_key': user.api_key,
            }
        })

    @ajax_request_class
    @detail_route(methods=['GET'])
    def generate_api_key(self, request, pk=None):
        """generates a new API key

        Returns::

            {
                'status': 'success',
                'api_key': the new api key
            }
        """
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)},
                                status=403)
        user.generate_key()
        return {
            'status': 'success',
            'api_key': User.objects.get(pk=pk).api_key
        }

    @api_endpoint_class
    @ajax_request_class
    def update(self, request, pk=None):
        """
        Updates the request's user's first name, last name, and email

        Payload::

            {
             'user': {
                      'first_name': :first_name,
                      'last_name': :last_name,
                      'email': :email
                    }
            }

        Returns::

            {
                'status': 'success',
                'user': {
                    'first_name': user's first name,
                    'last_name': user's last name,
                    'email': user's email,
                    'api_key': user's API key
                }
            }
        """
        body = request.data
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)},
                                status=403)
        json_user = body.get('user')
        user.first_name = json_user.get('first_name')
        user.last_name = json_user.get('last_name')
        user.email = json_user.get('email')
        user.username = json_user.get('email')
        user.save()
        return JsonResponse({
            'status': 'success',
            'user': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'api_key': user.api_key,
            }
        })

    @ajax_request_class
    @detail_route(methods=['PUT'])
    def set_password(self, request, pk=None):
        """
        sets/updates a user's password, follows the min requirement of
        django password validation settings in config/settings/common.py

        Payload::

            {
                'current_password': current_password,
                'password_1': password_1,
                'password_2': password_2
            }

        Returns::

            {
                'status': 'success'
            }
        """
        body = request.data
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)},
                                status=403)
        current_password = body.get('current_password')
        p1 = body.get('password_1')
        p2 = body.get('password_2')
        if not user.check_password(current_password):
            return JsonResponse({'status': 'error', 'message': 'current password is not valid'}, status=400)
        if p1 is None or p1 != p2:
            return JsonResponse({'status': 'error', 'message': 'entered password do not match'}, status=400)
        try:
            validate_password(p2)
        except ValidationError as e:
            return JsonResponse({'status': 'error', 'message': e.messages[0]}, status=400)
        user.set_password(p1)
        user.save()
        return JsonResponse({'status': 'success'})

    @ajax_request_class
    def get_actions(self, request):
        """returns all actions"""
        return {
            'status': 'success',
            'actions': PERMS.keys(),
        }

    @ajax_request_class
    @detail_route(methods=['GET'])
    def is_authorized(self, request, pk=None):
        """checks the auth for a given action, if user is the owner of the parent
        org then True is returned for each action

        Payload::

            {
                'organization_id': 2,
                'actions': ['can_invite_member', 'can_remove_member']
            }

        :param actions: from the json payload, a list of actions to check
        :returns: a dict of with keys equal to the actions, and values as bool
        """
        actions, org, error, message = self._parse_is_authenticated_params(request)
        if error:
            return JsonResponse({'status': 'error', 'message': message})

        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)},
                                status=403)

        auth = self._try_parent_org_auth(user, org, actions)
        if auth:
            return JsonResponse({'status': 'success', 'auth': auth})

        try:
            ou = OrganizationUser.objects.get(
                user=user, organization=org
            )
        except OrganizationUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'user does not exist'})

        auth = {action: PERMS[action](ou) for action in actions}
        return JsonResponse({'status': 'success', 'auth': auth})

    def _parse_is_authenticated_params(self, request):
        """checks if the org exists and if the actions are present

        :param request: the request
        :returns: tuple (actions, org, error, message)
        """
        error = False
        message = ""
        body = request.data
        if not body.get('actions'):
            message = 'no actions to check'
            error = True

        try:
            org = Organization.objects.get(pk=body.get('organization_id'))
        except Organization.DoesNotExist:
            message = 'organization does not exist'
            error = True
            org = None

        return body.get('actions'), org, error, message

    def _try_parent_org_auth(self, user, organization, actions):
        """checks the parent org for permissions, if the user is not the owner of
        the parent org, then None is returned.

        :param user: the request user
        :param organization_id: id of org to check its parent
        :param actions: list of str actions to check
        :returns: a dict of action permission resolutions or None
        """
        try:
            ou = OrganizationUser.objects.get(
                user=user,
                organization=organization.parent_org,
                role_level=ROLE_OWNER
            )
        except OrganizationUser.DoesNotExist:
            return None

        return {
            action: PERMS['requires_owner'](ou) for action in actions
        }

    @ajax_request_class
    @detail_route(methods=['GET'])
    def shared_buildings(self, request, pk=None):
        """gets the request user's ``show_shared_buildings`` attr"""
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)},
                                status=403)

        return JsonResponse({
            'status': 'success',
            'show_shared_buildings': user.show_shared_buildings,
        })

    @ajax_request_class
    @detail_route(methods=['GET'])
    def set_default_organization(self, request, pk=None):
        """sets the user's default organization"""
        body = request.data
        try:
            user = User.objects.get(pk=pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error', 'message': "Could not find user with pk = " + str(pk)}, status=404)
        if not user == request.user:
            return JsonResponse({'status': 'error', 'message': "Cannot access user account with pk = " + str(pk)},
                                status=403)

        org = body['organization']
        user.default_organization_id = org['id']
        user.save()
        return {'status': 'success'}

