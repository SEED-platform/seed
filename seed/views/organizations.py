# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser,
)
from seed.models import CanonicalBuilding
from seed.landing.models import SEEDUser as User
from seed.utils.api import api_endpoint_class
from seed.utils.organizations import create_organization
from seed.cleansing.models import (
    DATA_TYPES as CLEANSING_DATA_TYPES,
    SEVERITY as CLEANSING_SEVERITY,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets
from django.http import HttpResponse


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


_log = logging.getLogger(__name__)


class OrganizationViewSet(LoginRequiredMixin, viewsets.ViewSet):
    raise_exception = True

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

        return HttpResponse(json.dumps({'organizations': _dict_org(request, qs)}))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, pk=None):
        """
        Retrieves a single organization by id.
        ---
        """

        """
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
        org_id = pk  # request.query_params.get('organization_id', None)
        if org_id is None:
            return HttpResponse(json.dumps({
                'status': 'error',
                'message': 'no organization_id sent'
            }))

        try:
            org = Organization.objects.get(pk=org_id)
        except Organization.DoesNotExist:
            return HttpResponse(json.dumps({
                'status': 'error',
                'message': 'organization does not exist'
            }))
        if (
            not request.user.is_superuser and
            not OrganizationUser.objects.filter(
                user=request.user,
                organization=org,
                role_level__in=[ROLE_OWNER, ROLE_MEMBER, ROLE_VIEWER]
            ).exists()
        ):
            # TODO: better permission and return 401 or 403
            return HttpResponse(json.dumps({
                'status': 'error',
                'message': 'user is not the owner of the org'
            }))

        return HttpResponse(json.dumps({
            'status': 'success',
            'organization': _dict_org(request, [org])[0],
        }))

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    def create(self, request):
        """
        Creates a new organization.
        ---
        type:
            status:
                required: true
                type: string
                description: either success or error
            message:
                type: string
                description: error message, if any
            organization_id:
                required: true
                type: integer
                description: The ID of the new org, if created
        parameter_strategy: replace
        parameters:
            - name: organization_name
              description: "The name of the new organization"
              required: true
              paramType: string
            - name: user_id
              description: "The user id of the owner of the new org"
              required: true
              paramType: integer
        """
        body = request.data
        user = User.objects.get(pk=body['user_id'])
        org_name = body['organization_name']

        if Organization.objects.filter(name=org_name).exists():
            return HttpResponse(json.dumps({
                'status': 'error',
                'message': 'organization name already exists'
            }))

        org, _, _ = create_organization(user, org_name, org_name)
        return HttpResponse(json.dumps({'status': 'success',
                                        'message': 'organization created',
                                        'organization_id': org.pk}))
