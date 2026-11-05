"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.audit_template.audit_template import AUDIT_TEMPLATE_REPORT_TYPES, AuditTemplate
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import PropertyView
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper

PROGRESS_RESPONSE = AutoSchemaHelper.schema_factory(
    {
        "status": "string",
        "status_message": "string",
        "progress": "number",
        "progress_key": "string",
        "total": "integer",
        "unique_id": "integer",
        "func_name": "string",
    },
    description="Progress data of the started background task. Poll `/api/v3/progress/{progress_key}/` for its result.",
)


class AuditTemplateViewSet(viewsets.ViewSet, OrgMixin):
    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.path_id_field(description="Audit Template Submission ID."),
            AutoSchemaHelper.query_enum_field("report_format", "Report format. Defaults to pdf.", ["json", "xml", "pdf"], required=False),
        ],
        responses={
            (200, "application/pdf"): OpenApiTypes.BINARY,
            (200, "application/json"): OpenApiTypes.OBJECT,
            (200, "application/xml"): OpenApiTypes.STR,
        },
    )
    @method_decorator(
        [
            has_perm("can_view_data"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def get_submission(self, request, pk):
        """
        Fetches a Report Submission (JSON, XML, or PDF) from Audit Template (only)
        """
        # get report format or default to pdf
        default_report_format = "pdf"
        report_format = request.query_params.get("report_format", default_report_format)

        valid_file_formats = ["json", "xml", "pdf"]
        if report_format.lower() not in valid_file_formats:
            message = f"The report_format specified is invalid. Must be one of: {valid_file_formats}."
            return JsonResponse({"success": False, "message": message}, status=400)

        # retrieve report
        at = AuditTemplate(self.get_organization(self.request))
        response, message = at.get_submission(pk, report_format)

        # error
        if response is None:
            return JsonResponse({"success": False, "message": message}, status=400)
        # json
        if report_format.lower() == "json":
            return JsonResponse(json.loads(response.content))
        # xml
        if report_format.lower() == "xml":
            return HttpResponse(response.text, content_type="application/xml")
        # pdf
        response2 = HttpResponse(response.content)
        response2.headers["Content-Type"] = "application/pdf"
        response2.headers["Content-Disposition"] = f'attachment; filename="at_submission_{pk}.pdf"'
        return response2

    def validate_properties(self, properties):
        valid = [bool(properties)]
        for property in properties:
            valid.append(len(property) == 5)
            valid.append(property.get("audit_template_building_id"))
            valid.append(property.get("property_view"))
            valid.append(property.get("email"))
            valid.append(property.get("updated_at"))
            valid.append(property.get("name"))

        if not all(valid):
            return (
                False,
                "Request data must be structured as: {audit_template_building_id: integer, property_view: integer, name: string, email: string, updated_at: date time iso string 'YYYY-MM-DDTHH:MM:SSZ'}",
            )
        else:
            return True, ""

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ],
        request=AutoSchemaHelper.json_body({"property_view_ids": ["integer"]}, description="PropertyView IDs to be exported"),
        responses={200: PROGRESS_RESPONSE},
    )
    @method_decorator(
        [
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["POST"])
    def batch_export_to_audit_template(self, request):
        """
        Batch exports properties without Audit Template Building IDs to the linked Audit Template.
        SEED properties will be updated with the returned Audit Template Building ID.
        Properties outside the user's access level are skipped.
        """
        org_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)
        # only export properties within the user's access level instance subtree
        property_view_ids = list(
            PropertyView.objects.filter(
                id__in=request.data.get("property_view_ids", []),
                cycle__organization_id=org_id,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            ).values_list("id", flat=True)
        )

        at = AuditTemplate(org_id)

        progress_data, message = at.batch_export_to_audit_template(property_view_ids)
        if progress_data is None:
            return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)
        return JsonResponse(progress_data)

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("view_id", required=True, description="Property View ID to retrieve"),
        ],
        responses={(200, "application/xml"): OpenApiTypes.BINARY},
    )
    @method_decorator(
        [
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["GET"])
    def export_buildingsync_at_file(self, request):
        """
        Return the BuildingSync XML file that would be sent over to Audit Template.
        Mostly for testing or manual upload.
        """
        pk = request.GET.get("view_id", None)
        org_id = self.get_organization(self.request)
        access_level_instance = AccessLevelInstance.objects.get(pk=request.access_level_instance_id)

        try:
            property_view = PropertyView.objects.select_related("state").get(
                pk=pk,
                cycle__organization_id=org_id,
                property__access_level_instance__lft__gte=access_level_instance.lft,
                property__access_level_instance__rgt__lte=access_level_instance.rgt,
            )
        except PropertyView.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": f"Cannot match a PropertyView with pk={pk}"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            at = AuditTemplate(self.get_organization(request))
            xml, message = at.export_to_audit_template(property_view.state, None, file_only=True)
            if xml:
                return HttpResponse(xml, content_type="application/xml")
            else:
                return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(
            {"view_ids": ["integer"], "default_cycle": "integer"},
            description=(
                "- view_ids: PropertyView IDs to update. If empty [], all SEED properties will be used to determine the correct "
                "PropertyView\n- default_cycle: Cycle ID to import into when a submission does not match a cycle by date"
            ),
        ),
        responses={200: PROGRESS_RESPONSE},
    )
    @method_decorator(
        [
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["PUT"])
    def batch_get_city_submission_xml(self, request):
        """
        Batch import from Audit Template using the submissions endpoint for the organization's Audit Template city
        Properties are updated with xmls using custom_id_1 as matching criteria
        Properties outside the user's access level are skipped.
        """
        view_ids = request.data.get("view_ids", [])
        default_cycle = request.data.get("default_cycle", None)

        at = AuditTemplate(self.get_organization(request))
        progress_data, message = at.batch_get_city_submission_xml(view_ids, default_cycle, request.access_level_instance_id)

        if progress_data is None:
            return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)
        return JsonResponse(progress_data)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(
            {"city_id": "integer", "custom_id_1": "string"},
            required=["city_id", "custom_id_1"],
            description="custom_id_1 is matched against the submissions of the organization's Audit Template city (city_id is required but unused).",
        ),
        responses={200: PROGRESS_RESPONSE},
    )
    @method_decorator(
        [
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["PUT"])
    def get_city_submission_xml(self, request):
        """
        Import from Audit Template using the submissions endpoint for a given city
        Property are updated with returned xml using custom_id_1 as matching criteria
        Properties outside the user's access level are skipped.
        """
        city_id = request.data.get("city_id")
        if not city_id:
            return JsonResponse({"success": False, "message": "City ID argument required"}, status=400)
        custom_id_1 = request.data.get("custom_id_1")
        if not custom_id_1:
            return JsonResponse({"success": False, "message": "Custom ID argument required"}, status=400)

        at = AuditTemplate(self.get_organization(request))
        progress_data, message = at.get_city_submission_xml(custom_id_1, request.access_level_instance_id)

        if progress_data is None:
            return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)
        return JsonResponse(progress_data)

    @extend_schema(
        responses={200: AutoSchemaHelper.schema_factory({"status": "string", "data": ["string"]})},
    )
    @action(detail=False, methods=["GET"])
    def report_types(self, request):
        """
        Returns the canonical list of valid Audit Template report types (e.g., for populating a
        "Report Type" dropdown). This is not organization-specific.
        """
        return JsonResponse({"status": "success", "data": AUDIT_TEMPLATE_REPORT_TYPES})
