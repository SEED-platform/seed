# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from functools import wraps
from inspect import signature

from django.conf import settings
from django.http import HttpResponseForbidden

from seed.lib.superperms.orgs.models import (
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser
)
from seed.lib.superperms.orgs.permissions import get_org_id

# Allow Super Users to ignore permissions.
ALLOW_SUPER_USER_PERMS = getattr(settings, 'ALLOW_SUPER_USER_PERMS', True)


def requires_parent_org_owner(org_user):
    """Only allow owners of parent orgs to view child org perms."""
    return (
        org_user.role_level >= ROLE_OWNER and
        not org_user.organization.parent_org
    )


def requires_owner_or_superuser_without_org(org_user):
    """
    Allows superusers to use the endpoint with or without an organization_id
    Owners can only use the endpoint with an organization_id
    """
    return requires_owner(org_user) or requires_superuser(org_user)


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
    # requires_superuser is the only role that can be on organization-agnostic endpoints
    'requires_superuser': requires_superuser,
    'requires_parent_org_owner': requires_parent_org_owner,
    'requires_owner_or_superuser_without_org': requires_owner_or_superuser_without_org,
    'requires_owner': requires_owner,
    'requires_member': requires_member,
    'requires_viewer': requires_viewer,
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


# Return nothing if valid, otherwise return Forbidden response
def _validate_permissions(perm_name, request, requires_org):
    if not requires_org:
        if perm_name not in ['requires_superuser', 'requires_owner_or_superuser_without_org']:
            raise AssertionError('requires_org=False can only be combined with requires_superuser or '
                                 'requires_owner_or_superuser_without_org')
        if request.user.is_superuser:
            return
        elif perm_name != 'requires_owner_or_superuser_without_org':
            return _make_resp('perm_denied')

    org_id = get_org_id(request)
    try:
        org = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
        return _make_resp('org_dne')

    # Skip perms checks if settings allow super_users to bypass.
    if request.user.is_superuser and ALLOW_SUPER_USER_PERMS:
        return

    try:
        org_user = OrganizationUser.objects.get(
            user=request.user, organization=org
        )
    except OrganizationUser.DoesNotExist:
        return _make_resp('user_dne')

    if not PERMS.get(perm_name, lambda x: False)(org_user):
        return _make_resp('perm_denied')


def has_perm_class(perm_name: str, requires_org: bool = True):
    """Proceed if user from request has ``perm_name``."""

    def decorator(fn):
        params = list(signature(fn).parameters)
        if params and params[0] == 'self':
            @wraps(fn)
            def _wrapped(self, request, *args, **kwargs):
                return _validate_permissions(perm_name, request, requires_org) or fn(self, request, *args, **kwargs)
        else:
            @wraps(fn)
            def _wrapped(request, *args, **kwargs):
                return _validate_permissions(perm_name, request, requires_org) or fn(request, *args, **kwargs)

        return _wrapped

    return decorator
