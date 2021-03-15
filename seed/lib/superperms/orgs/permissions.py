# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.
:authors Paul Munday<paul@paulmunday.net> Fable Turas<fable@raintechpdx.com>

Provides permissions classes for use in DRF views and viewsets to control
access based on Organization and OrganizationUser.role_level.
"""
from django import VERSION as DJANGO_VERSION
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

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
            # Type case the organization_id as a integer
            if '_id' in org_str:
                org_id = int(org_id)
            break
    return org_id


def get_org_id(request):
    """Extract the organization ID from a request. Returns None if not found

    This function attempts to find the organization id by checking (in order):
    - Path of the request (e.g. /organizations/<id>/...)
    - Query parameters
    - Request body

    :param request:
    :return: str | None
    """
    # first check if the view is configured to get the org id from a path parameter
    request_view = request.parser_context.get('view', None)
    if request_view is not None and hasattr(request_view, 'authz_org_id_kwarg'):
        kwarg_name = request_view.authz_org_id_kwarg
        if kwarg_name:
            request_kwargs = request.parser_context.get('kwargs', {})
            # some views might not include the ID in the path so we have to check (e.g. data quality)
            kwarg_org_id = request_kwargs.get(kwarg_name, None)
            if kwarg_org_id is not None:
                return kwarg_org_id

    # if the view doesn't explicitly provide a kwarg for organization id in the path,
    # check the path string.
    # this is required for backwards compatibility of older APIs
    if hasattr(request, '_request') and 'organizations' in request._request.path:
        request_path = request._request.path.split('/')
        try:
            if request_path[3] == 'organizations' and request_path[4].isdigit():
                return int(request_path[4])
        except (IndexError, ValueError):
            # IndexError will occur if the split results in less than 4 tokens
            # ValueError will occur if the result is non-numeric somehow
            pass

    # Try to get it from the query parameters
    query_params_org_id = get_org_or_id(request.query_params)
    if query_params_org_id is not None:
        return query_params_org_id

    # try getting it from the request body itself
    try:
        if hasattr(request, 'data'):
            data_org_id = get_org_or_id(request.data)
            if data_org_id is not None:
                return data_org_id
    except ValueError:
        return None

    return None


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

        # Allow superuser to have permissions. This method is similar to the
        # previous has_perm method orgs/decorators.py:has_perm_class
        if request.user.is_superuser and ALLOW_SUPER_USER_PERMS:
            return True

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
        # Workaround to ensure this is not applied to the root view when using DefaultRouter.
        value_error = False
        try:
            if hasattr(view, 'get_queryset'):
                queryset = view.get_queryset()
            else:
                queryset = getattr(view, 'queryset', None)
        except ValueError:
            if not getattr(view, 'queryset', None):
                value_error = True
            else:
                value_error = False

        if value_error or queryset is None:
            raise AssertionError('Cannot apply {} on a view that does not set `.queryset`'
                                 ' or have a `.get_queryset()` method.'.format(view.__class__))

        return (
            request.user and
            (
                is_authenticated(request.user) or not self.authenticated_users_only
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
            has_perm = super().has_perm(request)
        return has_perm
