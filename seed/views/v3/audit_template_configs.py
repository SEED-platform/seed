"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import django.core.exceptions
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, status, viewsets

from seed.audit_template.audit_template import schedule_sync, toggle_audit_template_sync
from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import Organization
from seed.models.audit_template_configs import AuditTemplateConfig
from seed.serializers.audit_template_configs import AuditTemplateConfigSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper

CONFIG_REQUEST = {
    "application/json": {
        "type": "object",
        "properties": {
            "update_at_day": {
                "type": "integer",
                "minimum": 0,
                "maximum": 6,
                "nullable": True,
                "description": "Day of the week (0 is Sunday)",
            },
            "update_at_hour": {"type": "integer", "minimum": 0, "maximum": 23, "nullable": True},
            "update_at_minute": {"type": "integer", "minimum": 0, "maximum": 59, "nullable": True},
            "last_update_date": {"type": "string", "format": "date-time", "nullable": True},
            "timezone": {"type": "string", "description": "Timezone of the sync schedule. Defaults to the server's timezone"},
        },
    }
}


class AuditTemplateConfigResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = AuditTemplateConfigSerializer()


class AuditTemplateConfigUpdateResponseSerializer(AuditTemplateConfigResponseSerializer):
    data = AuditTemplateConfigSerializer(required=False)
    message = serializers.CharField(required=False, help_text='"No changes detected." when nothing was updated')


# the list's envelope is a single object
@extend_schema_serializer(many=False)
class AuditTemplateConfigListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = AuditTemplateConfigSerializer(many=True)


@extend_schema(parameters=[AutoSchemaHelper.query_org_id_field()])
class AuditTemplateConfigViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AuditTemplateConfigSerializer
    model = AuditTemplateConfig

    @extend_schema(responses=AuditTemplateConfigListResponseSerializer)
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    def list(self, request):
        org_id = self.get_organization(request)
        at_configs = AuditTemplateConfig.objects.filter(organization=org_id)

        at_data = AuditTemplateConfigSerializer(at_configs, many=True).data

        return JsonResponse({"status": "success", "data": at_data}, status=status.HTTP_200_OK)

    @extend_schema(request=CONFIG_REQUEST, responses={201: AuditTemplateConfigResponseSerializer})
    @method_decorator(
        [
            has_perm("requires_owner"),
        ]
    )
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

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("Audit Template Config ID")],
        request=CONFIG_REQUEST,
        responses=AuditTemplateConfigUpdateResponseSerializer,
    )
    @method_decorator(
        [
            has_perm("requires_owner"),
        ]
    )
    def update(self, request, pk):
        org_id = self.get_organization(self.request)

        try:
            atc = AuditTemplateConfig.objects.get(pk=pk, organization_id=org_id)
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

    @extend_schema(parameters=[AutoSchemaHelper.path_id_field("Audit Template Config ID")], responses={204: None})
    @method_decorator(
        [
            has_perm("requires_owner"),
        ]
    )
    def destroy(self, request, pk):
        org_id = self.get_organization(self.request)
        org = Organization.objects.get(pk=org_id)
        try:
            atc = AuditTemplateConfig.objects.get(pk=pk, organization_id=org_id)
            if org.audit_template_sync_enabled:
                toggle_audit_template_sync(org.audit_template_sync_enabled, org.id)
            atc.delete()

        except AuditTemplateConfig.DoesNotExist:
            return JsonResponse({"status": "error", "message": "No such resource."})

        return HttpResponse(status=204)


def add_org_to_data(org_id, data):
    """set the organization of the data to the request's organization"""
    data["organization"] = org_id
    return data


def changes_detected(old, new):
    """Identify the need to update the instance"""
    fields = ["organization", "update_at_day", "update_at_hour", "update_at_minute"]
    return any(old.get(field) != new.get(field) for field in fields)
