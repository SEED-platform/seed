# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.
:authors Paul Munday<paul@paulmunday.net> Fable Turas<fable@raintechpdx.com>

Provides permissions classes for use in DRF views and viewsets to control
access based on Organization and OrganizationUser.role_level.
"""
from django import VERSION as DJANGO_VERSION

from django.conf import settings

from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from seed.lib.superperms.orgs.models import (
    ROLE_OWNER,
    ROLE_MEMBER,
    ROLE_VIEWER,
    Organization,
    OrganizationUser
)

# Allow Super Users to ignore permissions.
ALLOW_SUPER_USER_PERMS = getattr(settings, 'ALLOW_SUPER_USER_PERMS', True)


# based on version present in newer version of rest_framework.compat
# replace when DRF is upgraded to relevant version
def is_authenticated(user):
    """Django >=1.10 use user.is_authenticated, not user.is_authenticated()"""
    # pragma: no cover
    if DJANGO_VERSION < (1, 10):
        return user.is_authenticated()
    return user.is_authenticated


def get_org_or_id(dictlike):
    """Get value of organization or organization_id"""
    # while documentation should encourage the use of one consistent key choice
    # for supplying an organization to query_params, we check all reasonable
    # permutations of organization id.
    org_query_strings = ['organization', 'organization_id', 'org_id', 'org']
    org_id = None
    for org_str in org_query_strings:
        org_id = dictlike.get(org_str)
        if org_id:
            break
    return org_id


def get_org_id(request):
    """Get org id from request"""
    org_id = get_org_or_id(request.query_params)
    if not org_id:
        if hasattr(request, 'data'):
            data = request.data
            org_id = get_org_or_id(data)
    return org_id


def get_user_org(user):
    """
    Provides a fallback organization retrieval for when id is not supplied
    by query params or request.data. Makes the assumption that, if set,
    default_organization would be the highest preference in organization
    selection, or that an available "parent" organization would logically
    precede a sub_org in the ranking of unspecified preference.

    :param user: User object from request.user
    :return: organization object from user profile default_organization
        attribute, if set, or first "parent" organization user is a member
         of, or first returned organization from user's orgs.
    """
    if user.default_organization:
        return user.default_organization
    else:
        orgs = user.orgs.all()
        parent_orgs = [org for org in orgs if org.child_orgs.all()]
        org = orgs[0]
        if parent_orgs:
            org = parent_orgs[0]
        return org


class SEEDOrgPermissions(BasePermission):
    """
    Control API permissions based on OrganizationUser and HTTP Method
    i.e. GET/POST etc.

    Any method that can change data (POST, PUT, PATCH,  DELETE) requires
    ROLE_MEMBER, the rest (GET, OPTIONS, HEAD) require ROLE_VIEWER.
    All require an authenticated user.

    Override perm_map (and subclass) to change these.

    Requires a queryset attribute on the API View(Set). Since we typically
    need to override get_queryset to ensure filtering by organization[#f1],
    you should typically  set to MyModel.objects.none().

    ..[#f1] You can use the OrgQuerySetMixin from seed.utils.api on your
    view(set)to do this.

    """
    message = PermissionDenied.default_detail
    authenticated_users_only = True
    perm_map = {
        'GET': ROLE_VIEWER,
        'OPTIONS': ROLE_VIEWER,
        'HEAD': ROLE_VIEWER,
        'POST': ROLE_MEMBER,
        'PUT': ROLE_MEMBER,
        'PATCH': ROLE_MEMBER,
        'DELETE': ROLE_MEMBER,
    }

    def has_perm(self, request):
        """Determine if user has required permission"""
        # pylint: disable=no-member
        has_perm = False
        # defaults to OWNER if not specified.
        required_perm = self.perm_map.get(request.method, ROLE_OWNER)
        org = None
        org_id = get_org_id(request)
        if not org_id:
            org = get_user_org(request.user)
            org_id = getattr(org, 'pk')
        try:
            org_user = OrganizationUser.objects.get(
                user=request.user, organization__id=org_id
            )
            has_perm = org_user.role_level >= required_perm
        except OrganizationUser.DoesNotExist:
            self.message = 'No relationship to organization'
            # return the right error message. we wait until here to check for
            # organization so the extra db call is not made if not needed.
            if not org:
                try:
                    org = Organization.objects.get(id=org_id)
                except Organization.DoesNotExist:
                    self.message = 'Organization does not exist'
        return has_perm

    def has_permission(self, request, view):
        """Determines if user has correct permissions, called by DRF."""
        # Workaround to ensure this is not applied
        # to the root view when using DefaultRouter.
        if hasattr(view, 'get_queryset'):
            queryset = view.get_queryset()
        else:
            queryset = getattr(view, 'queryset', None)

        assert queryset is not None, (
            'Cannot apply {} on a view that does not set `.queryset`'
            ' or have a `.get_queryset()` method.'.format(view.__class__)
        )
        return (
            request.user and
            (
                is_authenticated(request.user)
                or not self.authenticated_users_only
            )
            and self.has_perm(request)
        )


class SEEDPublicPermissions(SEEDOrgPermissions):
    """Allow anonymous users read-only access"""
    authenticated_users_only = False
    safe_methods = ['GET', 'OPTIONS', 'HEAD']

    def has_perm(self, request):
        """Always true for safe methods."""
        has_perm = False
        if request.method in self.safe_methods:
            has_perm = True
        elif is_authenticated(request.user):
            has_perm = super(SEEDPublicPermissions, self).has_perm(request)
        return has_perm
