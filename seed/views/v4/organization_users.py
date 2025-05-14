from django.http import JsonResponse
from rest_framework import generics, viewsets

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import OrganizationUser
from seed.serializers.organizations import OrganizationUserSerializer
from seed.utils.api import OrgMixin, api_endpoint_class


class OrganizationUserViewSet(generics.GenericAPIView, viewsets.ViewSet, OrgMixin):
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    def update(self, request, pk=None):
        """
        List all the properties for angular ag grid
        """
        organization_id = self.get_organization(request)
        try:
            org_user = OrganizationUser.objects.get(pk=pk, organization_id=organization_id)
        except OrganizationUser.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Organization User not found"}, status=404)

        data = request.data
        data["settings"] = request.data.get("settings", {})
        serializer = OrganizationUserSerializer(org_user, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({"status": "success", "data": serializer.data})
        else:
            return JsonResponse({"status": "error", "message": serializer.errors}, status=400)
