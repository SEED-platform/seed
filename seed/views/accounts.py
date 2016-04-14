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

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm, PERMS
from seed.lib.superperms.orgs.exceptions import TooManyNestedOrgs
from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser,
)
from seed.utils.buildings import get_columns as utils_get_columns
from seed.models import CanonicalBuilding
from seed.landing.models import SEEDUser as User
from seed.tasks import (
    invite_to_seed,
)
from seed.utils.api import api_endpoint
from seed.utils.organizations import create_organization
from seed.public.models import INTERNAL, PUBLIC, SharedBuildingField
from seed.cleansing.models import (
    CATEGORY_MISSING_MATCHING_FIELD,
    CATEGORY_MISSING_VALUES,
    CATEGORY_IN_RANGE_CHECKING,
    DATA_TYPES as CLEANSING_DATA_TYPES,
    SEVERITY as CLEANSING_SEVERITY,
    Rules
)


_log = logging.getLogger(__name__)


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


@api_endpoint
@ajax_request
@login_required
def get_organizations(request):
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
             'num_buildings': Count of buildings belonging to this org
            }...
           ]
        }
    """
    if request.user.is_superuser:
        qs = Organization.objects.all()
    else:
        qs = request.user.orgs.all()

    return {'organizations': _dict_org(request, qs)}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def get_organization(request):
    """
    Retrieves a single organization by id.

    :GET: Expects ?organization_id=(:org_id)

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
    org_id = request.GET.get('organization_id', None)
    if org_id is None:
        return {
            'status': 'error',
            'message': 'no organization_id sent'
        }

    try:
        org = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
        return {
            'status': 'error',
            'message': 'organization does not exist'
        }
    if (
        not request.user.is_superuser and
        not OrganizationUser.objects.filter(
            user=request.user,
            organization=org,
            role_level__in=[ROLE_OWNER, ROLE_MEMBER, ROLE_VIEWER]
        ).exists()
    ):
        # TODO: better permission and return 401 or 403
        return {
            'status': 'error',
            'message': 'user is not the owner of the org'
        }

    return {
        'status': 'success',
        'organization': _dict_org(request, [org])[0],
    }


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_member')
def get_organizations_users(request):
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
    body = json.loads(request.body)
    org = Organization.objects.get(pk=body['organization_id'])

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

    return {'status': 'success', 'users': users}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_owner')
def remove_user_from_org(request):
    """
    Removes a user from an organization.

    Payload::

        {
            'organization_id': ID of the org,
            'user_id': ID of the user
        }

    Returns::

        {
            'status': 'success' or 'error',
            'message': 'error message, if any'
        }

    """
    body = json.loads(request.body)
    if body.get('organization_id') is None:
        return {
            'status': 'error',
            'message': 'missing the organization_id'
        }
    try:
        org = Organization.objects.get(pk=body['organization_id'])
    except Organization.DoesNotExist:
        return {
            'status': 'error',
            'message': 'organization does not exist'
        }
    if body.get('user_id') is None:
        return {
            'status': 'error',
            'message': 'missing the user_id'
        }
    try:
        user = User.objects.get(pk=body['user_id'])
    except User.DoesNotExist:
        return {
            'status': 'error',
            'message': 'user does not exist'
        }

    if not OrganizationUser.objects.filter(
        user=request.user, organization=org, role_level=ROLE_OWNER
    ).exists():
        return {
            'status': 'error',
            'message': 'only the organization owner can remove a member'
        }

    is_last_member = not OrganizationUser.objects.filter(
        organization=org,
    ).exclude(user=user).exists()

    if is_last_member:
        return {
            'status': 'error',
            'message': 'an organization must have at least one member'
        }

    is_last_owner = not OrganizationUser.objects.filter(
        organization=org,
        role_level=ROLE_OWNER,
    ).exclude(user=user).exists()

    if is_last_owner:
        return {
            'status': 'error',
            'message': 'an organization must have at least one owner level member'
        }

    ou = OrganizationUser.objects.get(user=user, organization=org)
    ou.delete()

    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_parent_org_owner')
def add_org(request):
    """
    Creates a new organization.

    Payload::

        {
            'organization_name': The name of the new org,
            'user_id': the user id of the owner of the new org,
        }

    Returns::

        {
            'status': 'success' or 'error',
            'message': 'message, if any',
            'organization_id': The ID of the new org, if created.
        }

    """
    body = json.loads(request.body)
    user = User.objects.get(pk=body['user_id'])
    org_name = body['organization_name']

    if Organization.objects.filter(name=org_name).exists():
        return {
            'status': 'error',
            'message': 'organization name already exists'
        }

    org, _, _ = create_organization(user, org_name, org_name)
    return {'status': 'success',
            'message': 'organization created',
            'organization_id': org.pk}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_owner')
def add_user_to_organization(request):
    """
    Adds an existing user to an organization.

    Payload::

        {
            'organization_id': The ID of the organization,
            'user_id': the user id of the owner of the new org,
        }

    Returns::

        {
            'status': 'success' or 'error',
            'message': 'message, if any',
        }


    """
    body = json.loads(request.body)
    org = Organization.objects.get(pk=body['organization_id'])
    user = User.objects.get(pk=body['user_id'])

    org.add_member(user)

    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_owner')
def add_user(request):
    """
    Creates a new SEED user.  One of 'organization_id' or 'org_name' is needed.
    Sends invitation email to the new user.

    Payload::

        {
            'organization_id': ID of an existing org to add the new user to,
            'org_name': Name of a new org to create with user as owner
            'first_name': First name of new user
            'last_name': Last name of new user
            'role': {
                'value': The permission level of new user within this org
                    (one of member, viewer, owner)
            },
            'email': Email address of new user.
        }

    Returns::

        {
            'status': 'success',
            'message': email address of new user,
            'org': name of the new org (or existing org),
            'org_created': True if new org created,
            'username': Username of new user
        }


    """
    body = json.loads(request.body)
    org_name = body.get('org_name')
    org_id = body.get('organization_id')
    if ((org_name and org_id) or (not org_name and not org_id)):
        return {
            'status': 'error',
            'message': 'Choose either an existing org or provide a new one'
        }

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
    if body.get('role') and body.get('role', {}).get('value'):
        OrganizationUser.objects.filter(
            organization_id=org.pk,
            user_id=user.pk
        ).update(role_level=_get_role_from_js(body['role']['value']))

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

    return {'status': 'success', 'message': user.email, 'org': org.name,
            'org_created': org_created, 'username': user.username}


@ajax_request
@login_required
@has_perm('requires_superuser')
def get_users(request):
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

    return {'users': users}


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_owner')
def update_role(request):
    """
    Sets a user's role within an organization.

    Payload::

        {
            'organization_id': organization's id,
            'user_id': user's id,
            'role': one of 'owner', 'member', 'viewer'
        }

    Returns::

        {
            'status': 'success or error',
            'message': 'error message, if any'
        }
    """
    body = json.loads(request.body)
    role = _get_role_from_js(body['role'])

    user_id = body['user_id']

    organization_id = body['organization_id']

    is_last_member = not OrganizationUser.objects.filter(
        organization=organization_id,
    ).exclude(user=user_id).exists()

    if is_last_member:
        return {
            'status': 'error',
            'message': 'an organization must have at least one member'
        }

    is_last_owner = not OrganizationUser.objects.filter(
        organization=organization_id,
        role_level=ROLE_OWNER,
    ).exclude(user=user_id).exists()

    if is_last_owner:
        return {
            'status': 'error',
            'message': 'an organization must have at least one owner level member'
        }

    OrganizationUser.objects.filter(
        user_id=user_id,
        organization_id=body['organization_id']
    ).update(role_level=role)

    return {'status': 'success'}


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


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_owner')
def save_org_settings(request):
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
    org = Organization.objects.get(pk=body['organization_id'])
    posted_org = body.get('organization', None)
    if posted_org is None:
        return {'status': 'error', 'message': 'malformed request'}

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

    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
def get_query_threshold(request):
    """
    Returns the "query_threshold" for an org.  Searches from
    members of sibling orgs must return at least this many buildings
    from orgs they do not belong to, or else buildings from orgs they
    don't belong to will be removed from the results.

    :GET: Expects organization_id in the query string.

    Returns::

        {
         'status': 'success',
         'query_threshold': The minimum number of buildings that must be
             returned from a search to avoid squelching non-member-org results.
        }
    """
    org_id = request.GET.get('organization_id')
    org = Organization.objects.get(pk=org_id)
    return {
        'status': 'success',
        'query_threshold': org.query_threshold
    }


@api_endpoint
@ajax_request
@login_required
def get_shared_fields(request):
    """
    Retrieves all fields marked as shared for this org tree.

    :GET: Expects organization_id in the query string.

    Returns::

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
    org_id = request.GET.get('organization_id')
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

    return result


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_parent_org_owner')
def get_cleansing_rules(request):
    """
    Returns the cleansing rules for an org.

    :param request:
    :GET: Expects organization_id in the query string.

    Returns::

        {
         'status': 'success',
         'in_range_checking': An array of in-range error rules,
         'missing_matching_field': An array of fields to verify existence,
         'missing_values': An array of fields to ignore missing values
        }
    """
    org_id = request.GET.get('organization_id')
    org = Organization.objects.get(pk=org_id)

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

    return result


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_parent_org_owner')
def reset_cleansing_rules(request):
    """
    Resets an organization's data cleansing rules

    :param request:
    :GET: Expects organization_id in the query string.

    Returns::

        {
         'status': 'success',
         'in_range_checking': An array of in-range error rules,
         'missing_matching_field': An array of fields to verify existence,
         'missing_values': An array of fields to ignore missing values
        }
    """
    org_id = request.GET.get('organization_id')
    org = Organization.objects.get(pk=org_id)

    Rules.restore_defaults(org)
    return get_cleansing_rules(request)


@api_endpoint
@ajax_request
@login_required
@has_perm('requires_parent_org_owner')
def save_cleansing_rules(request):
    """
    Saves an organization's settings: name, query threshold, shared fields

    Payload::

        {
            'organization_id: 2,
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

    Returns::

        {
            'status': 'success',
        }
    """
    body = json.loads(request.body)
    if body.get('organization_id') is None:
        return {
            'status': 'error',
            'message': 'missing the organization_id'
        }
    try:
        org = Organization.objects.get(pk=body['organization_id'])
    except Organization.DoesNotExist:
        return {
            'status': 'error',
            'message': 'organization does not exist'
        }
    if body.get('cleansing_rules') is None:
        return {
            'status': 'error',
            'message': 'missing the cleansing_rules'
        }

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
    return {'status': 'success'}


@ajax_request
def search_public_fields(request):
    """Search across all public fields.

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
    from seed.views.main import _search_buildings
    _search_buildings(request)


@api_endpoint
@ajax_request
@login_required
def create_sub_org(request):
    """
    Creates a child org of a parent org.

    Payload::

        {
            'parent_org_id': ID of the parent org,
            'sub_org': {
                'name': Name of new sub org,
                'email': Email address of owner of sub org, which
                        must already exist
            }
        }

    Returns::

        {
            'status': 'success' or 'error',
            'message': Error message, if any,
            'organization_id': ID of newly-created org
        }

    """
    body = json.loads(request.body)
    org = Organization.objects.get(pk=body['parent_org_id'])
    email = body['sub_org']['email']
    try:
        user = User.objects.get(username=email)
    except User.DoesNotExist:
        return {
            'status': 'error',
            'message': 'User with email address (%s) does not exist' % email
        }
    sub_org = Organization.objects.create(
        name=body['sub_org']['name']
    )

    OrganizationUser.objects.get_or_create(user=user, organization=sub_org)

    sub_org.parent_org = org

    try:
        sub_org.save()
    except TooManyNestedOrgs:
        sub_org.delete()
        return {
            'status': 'error',
            'message': 'Tried to create child of a child organization.'
        }

    return {'status': 'success',
            'organization_id': sub_org.pk}


@ajax_request
@login_required
def get_actions(request):
    """returns all actions"""
    return {
        'status': 'success',
        'actions': PERMS.keys(),
    }


@ajax_request
@login_required
def is_authorized(request):
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
    actions, org, error, message = _parse_is_authenticated_params(request)
    if error:
        return {'status': 'error', 'message': message}

    auth = _try_parent_org_auth(request.user, org, actions)
    if auth:
        return {'status': 'success', 'auth': auth}

    try:
        ou = OrganizationUser.objects.get(
            user=request.user, organization=org
        )
    except OrganizationUser.DoesNotExist:
        return {'status': 'error', 'message': 'user does not exist'}

    auth = {action: PERMS[action](ou) for action in actions}
    return {'status': 'success', 'auth': auth}


def _parse_is_authenticated_params(request):
    """checks if the org exists and if the actions are present

    :param request: the request
    :returns: tuple (actions, org, error, message)
    """
    error = False
    message = ""
    body = json.loads(request.body)
    if not body.get('actions'):
        message = 'no actions to check'
        error = True

    try:
        org = Organization.objects.get(pk=body.get('organization_id'))
    except Organization.DoesNotExist:
        message = 'organization does not exist'
        error = True
        org = None

    return (body.get('actions'), org, error, message)


def _try_parent_org_auth(user, organization, actions):
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


@ajax_request
@login_required
def get_shared_buildings(request):
    """gets the request user's ``show_shared_buildings`` attr"""
    return {
        'status': 'success',
        'show_shared_buildings': request.user.show_shared_buildings,
    }


@ajax_request
@login_required
def set_default_organization(request):
    """sets the user's default organization"""
    body = json.loads(request.body)
    org = body['organization']
    request.user.default_organization_id = org['id']
    request.user.save()
    return {'status': 'success'}


@api_endpoint
@ajax_request
@login_required
def get_user_profile(request):
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
    return {
        'status': 'success',
        'user': {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'api_key': request.user.api_key,
        }
    }


@ajax_request
@login_required
def generate_api_key(request):
    """generates a new API key

    Returns::

        {
            'status': 'success',
            'api_key': the new api key
        }
    """
    request.user.generate_key()
    return {
        'status': 'success',
        'api_key': User.objects.get(pk=request.user.pk).api_key
    }


@api_endpoint
@ajax_request
@login_required
def update_user(request):
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
    body = json.loads(request.body)
    user = body.get('user')
    request.user.first_name = user.get('first_name')
    request.user.last_name = user.get('last_name')
    request.user.email = user.get('email')
    request.user.username = user.get('email')
    request.user.save()
    return {
        'status': 'success',
        'user': {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'api_key': request.user.api_key,
        }
    }


@ajax_request
@login_required
def set_password(request):
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
    if request.method != 'PUT':
        return {'status': 'error', 'message': 'only HTTP PUT allowed'}
    body = json.loads(request.body)
    current_password = body.get('current_password')
    p1 = body.get('password_1')
    p2 = body.get('password_2')
    if not request.user.check_password(current_password):
        return {'status': 'error', 'message': 'current password is not valid'}
    if p1 is None or p1 != p2:
        return {'status': 'error', 'message': 'entered password do not match'}
    try:
        validate_password(p2)
    except ValidationError as e:
        return {'status': 'error', 'message': e.messages[0]}
    request.user.set_password(p1)
    request.user.save()
    return {'status': 'success'}
