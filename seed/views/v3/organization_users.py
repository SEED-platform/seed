"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.decorators import ajax_request_class
from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import ROLE_MEMBER, ROLE_OWNER, Organization, OrganizationUser
from seed.tasks import invite_to_organization
from seed.utils.api import api_endpoint_class
from seed.utils.users import get_js_role


class OrganizationUserViewSet(viewsets.ViewSet):
    # allow using `organization_pk` in url path for authorization (i.e., for has_perm_class)
    authz_org_id_kwarg = "organization_pk"

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    def list(self, request, organization_pk):
        """
        Retrieve all users belonging to an org.
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
        except ObjectDoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Could not retrieve organization at organization_pk = " + str(organization_pk)},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.user.is_superuser:
            is_member_or_superuser = True
            org_users = org.organizationuser_set.all()
        else:
            org_user = OrganizationUser.objects.get(user=self.request.user, organization=org)
            is_member_or_superuser = org_user.role_level >= ROLE_MEMBER

            org_users = org.organizationuser_set.filter(
                access_level_instance__rgt__lte=org_user.access_level_instance.rgt,
                access_level_instance__lft__gte=org_user.access_level_instance.lft,
            )

        users = []
        for u in org_users:
            user = u.user
            user_info = {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_id": user.pk,
            }
            if is_member_or_superuser:
                user_orgs = OrganizationUser.objects.filter(user=user).count()
                user_info.update(
                    {
                        "number_of_orgs": user_orgs,
                        "role": get_js_role(u.role_level),
                        "access_level_instance_id": u.access_level_instance.id,
                        "access_level_instance_name": u.access_level_instance.name,
                        "access_level": org.access_level_names[u.access_level_instance.depth - 1],
                    }
                )

            users.append(user_info)

        return JsonResponse({"status": "success", "users": users})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    @action(detail=True, methods=["PUT"])
    def add(self, request, organization_pk, pk):
        """
        Adds an existing user to an organization as an owner.
        """
        org = Organization.objects.get(pk=organization_pk)
        user = User.objects.get(pk=pk)

        try:
            created = org.add_member(user, org.root.id)
        except IntegrityError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Send an email if a new user has been added to the organization
        if created:
            try:
                domain = request.get_host()
            except Exception:
                domain = "seed-platform.org"
            invite_to_organization(domain, user, request.user.username, org)

        return JsonResponse({"status": "success"})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    @action(detail=True, methods=["DELETE"])
    def remove(self, request, organization_pk, pk):
        """
        Removes a user from an organization.
        """
        try:
            org = Organization.objects.get(pk=organization_pk)
        except Organization.DoesNotExist:
            return JsonResponse({"status": "error", "message": "organization does not exist"}, status=status.HTTP_404_NOT_FOUND)

        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "user does not exist"}, status=status.HTTP_404_NOT_FOUND)

        # A super user can remove a user. The superuser logic is also part of the decorator which
        # checks if super permissions have been limited per the ALLOW_SUPER_USER_PERMS setting.
        org_owner = OrganizationUser.objects.filter(user=request.user, organization=org, role_level=ROLE_OWNER).exists()
        if not request.user.is_superuser and not org_owner:
            return JsonResponse(
                {"status": "error", "message": "only the organization owner or superuser can remove a member"},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_last_member = (
            not OrganizationUser.objects.filter(
                organization=org,
            )
            .exclude(user=user)
            .exists()
        )

        if is_last_member:
            return JsonResponse(
                {"status": "error", "message": "an organization must have at least one member"}, status=status.HTTP_409_CONFLICT
            )

        is_last_owner = (
            not OrganizationUser.objects.filter(
                organization=org,
                role_level=ROLE_OWNER,
            )
            .exclude(user=user)
            .exists()
        )

        if is_last_owner:
            return JsonResponse(
                {"status": "error", "message": "an organization must have at least one owner level member"}, status=status.HTTP_409_CONFLICT
            )

        ou = OrganizationUser.objects.get(user=user, organization=org)
        ou.delete()

        # check the user and make sure they still have a valid organization to belong to
        user_orgs = OrganizationUser.objects.filter(user=user)

        if user_orgs.count() == 0:
            user.default_organization_id = None
            user.save()
        elif user.default_organization == org:
            first_org = user_orgs.order_by("id").first()
            user.default_organization = first_org.organization
            user.save()

        return JsonResponse({"status": "success"})
