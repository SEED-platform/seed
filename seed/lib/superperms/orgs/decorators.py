# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
from functools import wraps

from django.conf import settings
from django.http import HttpResponseForbidden

from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser
)

# Allow Super Users to ignore permissions.
ALLOW_SUPER_USER_PERMS = getattr(settings, 'ALLOW_SUPER_USER_PERMS', True)


def requires_parent_org_owner(org_user):
    """Only allow owners of parent orgs to view child org perms."""
    return (
        org_user.role_level >= ROLE_OWNER and
        not org_user.organization.parent_org
    )


def requires_owner(org_user):
    """Owners, and only owners have owner perms."""
    is_parent_org_owner = False
    parent = org_user.organization.parent_org
    if parent:
        is_parent_org_owner = OrganizationUser.objects.filter(
            organization=parent, user=org_user.user, role_level__gte=ROLE_OWNER
        ).exists()
    return is_parent_org_owner or org_user.role_level >= ROLE_OWNER


def requires_member(org_user):
    """Members and owners are considered to have member perms."""
    return org_user.role_level >= ROLE_MEMBER


def requires_viewer(org_user):
    """Everybody is considered to have viewer perms."""
    return org_user.role_level >= ROLE_VIEWER


def requires_superuser(org_user):
    """Only Django superusers have superuser perms."""
    return org_user.user.is_superuser


def can_create_sub_org(org_user):
    return requires_parent_org_owner(org_user)


def can_remove_org(org_user):
    return requires_parent_org_owner(org_user)


def can_invite_member(org_user):
    return org_user.role_level >= ROLE_OWNER


def can_remove_member(org_user):
    return org_user.role_level >= ROLE_OWNER


def can_modify_member_roles(org_user):
    return org_user.role_level >= ROLE_OWNER


def can_modify_query_thresh(org_user):
    return requires_parent_org_owner(org_user)


def can_modify_org_settings(org_user):
    """
    Owners of an org can modify its settings (fields, name, query threshold)
    and a suborg's settings can also be modified by its parent's owner.
    """
    # check for ownership of this org (and that it has no parent)
    if requires_parent_org_owner(org_user):
        return True
    # otherwise, there may be a parent org, so see if this user
    # is an owner of the parent.
    org = org_user.organization
    if org.parent_org is not None and org.parent_org.is_owner(org_user.user):
        return True
    return False


def can_view_sub_org_settings(org_user):
    return org_user.role_level >= ROLE_OWNER


def can_view_sub_org_fields(org_user):
    return requires_parent_org_owner(org_user)


def can_modify_data(org_user):
    return org_user.role_level >= ROLE_MEMBER


def can_view_data(org_user):
    return org_user.role_level >= ROLE_VIEWER


PERMS = {
    'requires_parent_org_owner': requires_parent_org_owner,
    'requires_owner': requires_owner,
    'requires_member': requires_member,
    'requires_viewer': requires_viewer,
    'requires_superuser': requires_superuser,
    'can_create_sub_org': can_create_sub_org,
    'can_remove_org': can_remove_org,
    'can_invite_member': can_invite_member,
    'can_remove_member': can_remove_member,
    'can_modify_member_roles': can_modify_member_roles,
    'can_modify_org_settings': can_modify_org_settings,
    'can_modify_query_thresh': can_modify_query_thresh,
    'can_view_sub_org_settings': can_view_sub_org_settings,
    'can_view_sub_org_fields': can_view_sub_org_fields,
    'can_modify_data': can_modify_data,
    'can_view_data': can_view_data
}

ERROR_MESSAGES = {
    'org_dne': 'Organization does not exist',
    'user_dne': 'No relationship to organization',
    'perm_denied': 'Permission denied',
}
RESPONSE_TEMPLATE = {'status': 'error', 'message': ''}


def _make_resp(message_name):
    """Return Http Error response with appropriate message."""
    resp_json = RESPONSE_TEMPLATE.copy()
    resp_json['message'] = ERROR_MESSAGES.get(
        message_name, 'Permission denied'
    )
    return HttpResponseForbidden(
        json.dumps(resp_json),
        content_type='application/json'
    )


def _get_org_id(request):
    """Extract the ``organization_id`` regardless of HTTP method type."""
    # first try to get it from the query parameters
    org_id = request.GET.get('organization_id')
    # if that does not work...
    if org_id is None:
        # try getting it from the request body itself
        if hasattr(request, 'data'):
            body = request.data
            org_id = body.get('organization_id', None)
        else:
            body = request.body
            org_id = json.loads(body).get('organization_id', None)
        if org_id is None:
            # if that does not work, try getting it from the url path itself, i.e. '/api/v2/organizations/12/'
            if hasattr(request, '_request') and 'organizations' in request._request.path:
                try:
                    org_id = int(request._request.path.split('/')[4])
                except (IndexError, ValueError):
                    # IndexError will occur if the split results in less than 4 tokens
                    # ValueError will occur if the result is non-numeric somehow
                    return None
            else:
                return None
    return org_id


def has_perm(perm_name):
    """Proceed if user from request has ``perm_name``."""

    def decorator(fn):
        @wraps(fn)
        def _wrapped(request, *args, **kwargs):
            # Skip perms checks if settings allow super_users to bypass.
            if request.user.is_superuser and ALLOW_SUPER_USER_PERMS:
                return fn(request, *args, **kwargs)

            org_id = _get_org_id(request)

            try:
                org = Organization.objects.get(pk=org_id)
            except Organization.DoesNotExist:
                return _make_resp('org_dne')

            try:
                org_user = OrganizationUser.objects.get(
                    user=request.user, organization=org
                )
            except OrganizationUser.DoesNotExist:
                return _make_resp('user_dne')

            if not PERMS.get(perm_name, lambda x: False)(org_user):
                return _make_resp('perm_denied')

            # Logic to see if person has permission required.
            return fn(request, *args, **kwargs)

        return _wrapped

    return decorator


def has_perm_class(perm_name):
    """Proceed if user from request has ``perm_name``."""

    def decorator(fn):
        @wraps(fn)
        def _wrapped(self, request, *args, **kwargs):
            # Skip perms checks if settings allow super_users to bypass.
            if request.user.is_superuser and ALLOW_SUPER_USER_PERMS:
                return fn(self, request, *args, **kwargs)

            org_id = _get_org_id(request)

            try:
                org = Organization.objects.get(pk=org_id)
            except Organization.DoesNotExist:
                return _make_resp('org_dne')

            try:
                org_user = OrganizationUser.objects.get(
                    user=request.user, organization=org
                )
            except OrganizationUser.DoesNotExist:
                return _make_resp('user_dne')

            if not PERMS.get(perm_name, lambda x: False)(org_user):
                return _make_resp('perm_denied')

            # Logic to see if person has permission required.
            return fn(self, request, *args, **kwargs)

        return _wrapped

    return decorator
