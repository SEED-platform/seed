"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json

from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.audit_template.audit_template import AuditTemplate
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import PropertyView
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper


class AuditTemplateViewSet(viewsets.ViewSet, OrgMixin):
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.base_field(
                name="id", location_attr="IN_PATH", type_attr="TYPE_INTEGER", required=True, description="Audit Template Submission ID."
            ),
            AutoSchemaHelper.query_string_field("report_format", False, "Report format Valid values are: xml, pdf. Defaults to pdf."),
        ]
    )
    @method_decorator(
        [
            has_perm("can_view_data"),
        ]
    )
    @action(detail=True, methods=["GET"])
    def get_submission(self, request, pk):
        """
        Fetches a Report Submission (XML or PDF) from Audit Template (only)
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
            return HttpResponse(response.text)
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

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("cycle_id", required=True, description="Cycle ID"),
        ],
        request_body=AutoSchemaHelper.schema_factory({"property_view_ids": ["integer"]}, description="PropertyView IDs to be exported"),
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
        SEED properties will be updated with the returned Audit Template Building ID
        """
        property_view_ids = request.data.get("property_view_ids", [])

        at = AuditTemplate(self.get_organization(request))

        progress_data, message = at.batch_export_to_audit_template(property_view_ids)
        if progress_data is None:
            return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)
        return JsonResponse(progress_data)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("view_id", required=True, description="Property View ID to retrieve"),
        ]
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

        try:
            property_view = PropertyView.objects.select_related("state").get(pk=pk, cycle__organization_id=org_id)
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

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory(
            {"city_id": "integer", "view_ids": ["integer"]},
            description="if view_ids is empty [] all SEED properties will be used to determine the correct PropertyView",
        ),
    )
    @method_decorator(
        [
            has_perm("can_modify_data"),
        ]
    )
    @action(detail=False, methods=["PUT"])
    def batch_get_city_submission_xml(self, request):
        """
        Batch import from Audit Template using the submissions endpoint for a given city
        Properties are updated with xmls using custom_id_1 as matching criteria
        """
        view_ids = request.data.get("view_ids", [])
        default_cycle = request.data.get("default_cycle", None)

        at = AuditTemplate(self.get_organization(request))
        progress_data, message = at.batch_get_city_submission_xml(view_ids, default_cycle)

        if progress_data is None:
            return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)
        return JsonResponse(progress_data)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=AutoSchemaHelper.schema_factory({"city_id": "integer", "custom_id_1": "string"}),
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
        """
        city_id = request.data.get("city_id")
        if not city_id:
            return JsonResponse({"success": False, "message": "City ID argument required"}, status=400)
        custom_id_1 = request.data.get("custom_id_1")
        if not custom_id_1:
            return JsonResponse({"success": False, "message": "Custom ID argument required"}, status=400)

        at = AuditTemplate(self.get_organization(request))
        progress_data, message = at.get_city_submission_xml(custom_id_1)

        if progress_data is None:
            return JsonResponse({"success": False, "message": message or "Unexpected Error"}, status=400)
        return JsonResponse(progress_data)
