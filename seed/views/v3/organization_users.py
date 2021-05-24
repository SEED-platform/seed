# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from seed.decorators import ajax_request_class
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (ROLE_OWNER,
                                             Organization,
                                             OrganizationUser)
from seed.tasks import invite_to_organization
from seed.utils.api import api_endpoint_class
from seed.views.v3.organizations import _get_js_role


class OrganizationUserViewSet(viewsets.ViewSet):
    # allow using `organization_pk` in url path for authorization (ie for has_perm_class)
    authz_org_id_kwarg = 'organization_pk'

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request, organization_pk):
        """
        Retrieve all users belonging to an org.
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse({'status': 'error',
                                 'message': 'Could not retrieve organization at organization_pk = ' + str(organization_pk)},
                                status=status.HTTP_404_NOT_FOUND)
        users = []
        for u in org.organizationuser_set.all():
            user = u.user

            user_orgs = OrganizationUser.objects.filter(user=user).count()

            users.append({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'number_of_orgs': user_orgs,
                'user_id': user.pk,
                'role': _get_js_role(u.role_level)
            })

        return JsonResponse({'status': 'success', 'users': users})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['PUT'])
    def add(self, request, organization_pk, pk):
        """
        Adds an existing user to an organization.
        """
        org = Organization.objects.get(pk=organization_pk)
        user = User.objects.get(pk=pk)

        _orguser, status = org.add_member(user)

        # Send an email if a new user has been added to the organization
        if status:
            try:
                domain = request.get_host()
            except Exception:
                domain = 'seed-platform.org'
            invite_to_organization(
                domain, user, request.user.username, org
            )

        return JsonResponse({'status': 'success'})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=True, methods=['DELETE'])
    def remove(self, request, organization_pk, pk):
        """
        Removes a user from an organization.
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
        except Organization.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'organization does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'user does not exist'
            }, status=status.HTTP_404_NOT_FOUND)

        # A super user can remove a user. The superuser logic is also part of the decorator which
        # checks if super permissions have been limited per the ALLOW_SUPER_USER_PERMS setting.
        org_owner = OrganizationUser.objects.filter(
            user=request.user, organization=org, role_level=ROLE_OWNER
        ).exists()
        if not request.user.is_superuser and not org_owner:
            return JsonResponse({
                'status': 'error',
                'message': 'only the organization owner or superuser can remove a member'
            }, status=status.HTTP_403_FORBIDDEN)

        is_last_member = not OrganizationUser.objects.filter(
            organization=org,
        ).exclude(user=user).exists()

        if is_last_member:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one member'
            }, status=status.HTTP_409_CONFLICT)

        is_last_owner = not OrganizationUser.objects.filter(
            organization=org,
            role_level=ROLE_OWNER,
        ).exclude(user=user).exists()

        if is_last_owner:
            return JsonResponse({
                'status': 'error',
                'message': 'an organization must have at least one owner level member'
            }, status=status.HTTP_409_CONFLICT)

        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.delete()

        # check the user and make sure they still have a valid organization to belong to
        user_orgs = OrganizationUser.objects.filter(user=user)

        if user_orgs.count() == 0:
            user.default_organization_id = None
            user.save()
        elif user.default_organization == org:
            first_org = user_orgs.order_by('id').first()
            user.default_organization = first_org.organization
            user.save()

        return JsonResponse({'status': 'success'})
