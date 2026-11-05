"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Cycle, FilterGroup, ReportConfiguration
from seed.serializers.report_configurations import ReportConfigurationSerializer
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

REPORT_CONFIGURATION_BODY = {
    "name": "string",
    "access_level_instance_id": "integer",
    "access_level_depth": "integer",
    "cycles": ["integer"],
    "x_column": "string",
    "y_column": "string",
    "filter_group_id": "integer",
}
optional_org_id_field = AutoSchemaHelper.query_org_id_field(
    required=False, description="Organization ID (defaults to your default organization)"
)


@extend_schema_view(
    list=extend_schema(parameters=[optional_org_id_field]),
    retrieve=extend_schema(parameters=[optional_org_id_field]),
)
class ReportConfigurationViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """An organization's saved report configurations"""

    model = ReportConfiguration
    serializer_class = ReportConfigurationSerializer

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(REPORT_CONFIGURATION_BODY, required=["name"]),
        responses={201: ReportConfigurationSerializer},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def create(self, request):
        org_id = self.get_organization(request)

        body = dict(request.data)
        name = body.get("name")
        access_level_instance_id = body.get("access_level_instance_id")
        cycle_ids = body.get("cycles")
        x_column = body.get("x_column")
        y_column = body.get("y_column")
        filter_group_id = body.get("filter_group_id")
        access_level_depth = body.get("access_level_depth")

        if not name:
            return JsonResponse({"success": False, "message": "name is missing"}, status=status.HTTP_400_BAD_REQUEST)
        if (
            access_level_instance_id
            and not AccessLevelInstance.objects.filter(pk=access_level_instance_id, organization_id=org_id).exists()
        ):
            return JsonResponse({"success": False, "message": "ALI does not exist"}, status=status.HTTP_400_BAD_REQUEST)
        if filter_group_id and not FilterGroup.objects.filter(pk=filter_group_id, organization_id=org_id).exists():
            return JsonResponse({"success": False, "message": "No such filter group"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rc = ReportConfiguration.objects.create(
                name=name,
                organization_id=org_id,
                access_level_instance_id=access_level_instance_id,
                access_level_depth=access_level_depth,
                x_column=x_column,
                y_column=y_column,
                filter_group_id=filter_group_id,
            )
        except IntegrityError as e:
            return JsonResponse({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if cycle_ids:
            rc.cycles.set(Cycle.objects.filter(pk__in=cycle_ids, organization_id=org_id))

        result = {
            "status": "success",
            "data": ReportConfigurationSerializer(rc).data,
        }

        return JsonResponse(result, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        request=AutoSchemaHelper.json_body(REPORT_CONFIGURATION_BODY),
        responses={200: ReportConfigurationSerializer},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def update(self, request, pk=None):
        """
        Update the given fields of a report configuration. `x_column` and `y_column` are cleared when omitted.
        """
        org_id = self.get_organization(request)
        try:
            rc = ReportConfiguration.objects.get(pk=pk, organization_id=org_id)
        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "message": "Cannot find report configuration"}, status=status.HTTP_404_NOT_FOUND)

        if "name" in request.data:
            rc.name = request.data["name"]

        if "access_level_instance_id" in request.data:
            if request.data["access_level_instance_id"] is not None:
                try:
                    ali = AccessLevelInstance.objects.get(pk=request.data["access_level_instance_id"], organization_id=org_id)
                    rc.access_level_instance = ali
                except ObjectDoesNotExist:
                    return JsonResponse({"success": False, "message": "ALI does not exist"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                rc.access_level_instance = None

        if "access_level_depth" in request.data:
            rc.access_level_depth = request.data["access_level_depth"]

        if "cycles" in request.data:
            if request.data["cycles"] is not None:
                try:
                    cycle_ids = request.data["cycles"]
                    rc.cycles.set(Cycle.objects.filter(pk__in=cycle_ids, organization_id=org_id))
                except ObjectDoesNotExist:
                    return JsonResponse({"success": False, "message": "Bad cycles"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                rc.cycles.set([])

        rc.x_column = request.data.get("x_column", None)
        rc.y_column = request.data.get("y_column", None)

        if "filter_group_id" in request.data:
            if request.data["filter_group_id"] is not None and request.data["filter_group_id"] != "":
                try:
                    fg = FilterGroup.objects.get(pk=request.data["filter_group_id"], organization_id=org_id)
                    rc.filter_group = fg
                except ObjectDoesNotExist:
                    return JsonResponse({"success": False, "message": "No such filter group"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                rc.filter_group = None

        rc.save()
        result = {
            "status": "success",
            "data": ReportConfigurationSerializer(rc).data,
        }
        return JsonResponse(result, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={204: OpenApiResponse(description="Report configuration deleted")},
    )
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def destroy(self, request, pk=None):
        try:
            ReportConfiguration.objects.get(pk=pk, organization_id=self.get_organization(request)).delete()
        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "message": "Cannot find report configuration"}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({"success": True, "message": "Report Configuration deleted"}, status=status.HTTP_204_NO_CONTENT)
