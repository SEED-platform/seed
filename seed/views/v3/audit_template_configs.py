"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

import django.core.exceptions
from django.http import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets

from seed.audit_template.audit_template import schedule_sync, toggle_audit_template_sync
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.audit_template_configs import AuditTemplateConfig
from seed.serializers.audit_template_configs import AuditTemplateConfigSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper, swagger_auto_schema_org_query_param


class AuditTemplateConfigViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AuditTemplateConfigSerializer
    model = AuditTemplateConfig

    @swagger_auto_schema_org_query_param
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_owner")
    def list(self, request):
        org_id = self.get_organization(request)
        at_configs = AuditTemplateConfig.objects.filter(organization=org_id)

        at_data = AuditTemplateConfigSerializer(at_configs, many=True).data

        return JsonResponse({"status": "success", "data": at_data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ]
    )
    @has_perm_class("requires_owner")
    def create(self, request):
        org_id = self.get_organization(self.request)
        data = add_org_to_data(org_id, request.data)

        serializer = AuditTemplateConfigSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            serializer.save()
            schedule_sync(data, org_id)
            # run code
        except django.core.exceptions.ValidationError as e:
            return JsonResponse({"status": "error", "message": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({"status": "success", "data": serializer.data}, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ]
    )
    @has_perm_class("requires_owner")
    def update(self, request, pk):
        org_id = self.get_organization(self.request)

        try:
            atc = AuditTemplateConfig.objects.get(pk=pk)
            old_data = AuditTemplateConfigSerializer(atc).data
        except AuditTemplateConfig.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        data = add_org_to_data(org_id, request.data)
        serializer = AuditTemplateConfigSerializer(atc, data=data)

        if not serializer.is_valid():
            return JsonResponse(
                {"status": "error", "message": "Bad Request", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )

        if not changes_detected(old_data, data):
            return JsonResponse({"status": "success", "message": "No changes detected."}, status=status.HTTP_200_OK)

        serializer.save()
        schedule_sync(data, org_id)

        return JsonResponse({"status": "success", "data": serializer.data}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ]
    )
    @has_perm_class("requires_owner")
    def delete(self, request, pk):
        org_id = self.get_organization(self.request)
        org = Organization.objects.get(pk=org_id)
        try:
            atc = AuditTemplateConfig.objects.get(pk=pk)
            if org.audit_template_sync_enabled:
                toggle_audit_template_sync()
            atc.delete()

        except AuditTemplateConfig.DoesNotExist:
            return JsonResponse({"stauts": "error", "message": "No such resource."})

        return HttpResponse(status=204)


def add_org_to_data(org_id, data):
    """add organization to data if it does not exist"""
    data["organization"] = data.get("organization", org_id)
    return data


def changes_detected(old, new):
    """Identify the need to update the instnace"""
    fields = ["organization", "update_at_day", "update_at_hour", "update_at_minute"]
    return any(old.get(field) != new.get(field) for field in fields)
