"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import OrganizationUser
from seed.serializers.organizations import OrganizationUserSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper


class OrganizationUserViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin):
    queryset = OrganizationUser.objects.none()
    serializer_class = OrganizationUserSerializer

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(
            {"settings": "object"},
            description="Properties:\n"
            "- settings: The user's saved settings (e.g., cycle, profile, sorts, and filters); omitting it clears them\n\n"
            "Superusers may also update `role_level`, `status`, and `user`.",
        ),
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "data": {
                        "settings": "object",
                        "role_level": "integer",
                        "status": "string",
                        "organization": "integer",
                        "user": "integer",
                        "email": "string",
                        "first_name": "string",
                        "last_name": "string",
                    },
                }
            )
        },
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
    def update(self, request, pk=None):
        """
        Updates an organization user's settings. Users other than superusers can only update their own settings.
        """
        organization_id = self.get_organization(request)
        org_users = OrganizationUser.objects.filter(organization_id=organization_id)
        if not request.user.is_superuser:
            org_users = org_users.filter(user=request.user)
        try:
            org_user = org_users.get(pk=pk)
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Organization User not found"}, status=404)

        # Only superusers can change anything other than settings (roles are managed by the users API)
        data = request.data if request.user.is_superuser else {}
        data["settings"] = request.data.get("settings", {})
        serializer = OrganizationUserSerializer(org_user, data=data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return JsonResponse({"status": "success", "data": serializer.data})
        else:
            return JsonResponse({"status": "error", "message": serializer.errors}, status=400)
