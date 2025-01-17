"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Cycle, FilterGroup, ReportConfiguration
from seed.serializers.report_configurations import ReportConfigurationSerializer
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


class ReportConfigurationViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    model = ReportConfiguration
    serializer_class = ReportConfigurationSerializer

    @swagger_auto_schema_org_query_param
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
            rc.cycles.set(Cycle.objects.filter(pk__in=cycle_ids))

        result = {
            "status": "success",
            "data": ReportConfigurationSerializer(rc).data,
        }

        return JsonResponse(result, status=status.HTTP_201_CREATED)

    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def update(self, request, pk=None):
        rc = ReportConfiguration.objects.get(pk=pk)

        if "name" in request.data:
            rc.name = request.data["name"]

        if "access_level_instance_id" in request.data:
            if request.data["access_level_instance_id"] is not None:
                try:
                    ali = AccessLevelInstance.objects.get(pk=request.data["access_level_instance_id"])
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
                    rc.cycles.set(Cycle.objects.filter(pk__in=cycle_ids))
                except ObjectDoesNotExist:
                    return JsonResponse({"success": False, "message": "Bad cycles"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                rc.cycles.set([])

        rc.x_column = request.data.get("x_column", None)
        rc.y_column = request.data.get("y_column", None)

        if "filter_group_id" in request.data:
            if request.data["filter_group_id"] is not None and request.data["filter_group_id"] != "":
                try:
                    fg = FilterGroup.objects.get(pk=request.data["filter_group_id"])
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

    @swagger_auto_schema_org_query_param
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_root_member_access"),
        ]
    )
    def destroy(self, request, pk=None):
        try:
            ReportConfiguration.objects.get(pk=pk).delete()
        except ObjectDoesNotExist:
            return JsonResponse({"success": False, "message": "Cannot find report configuration"}, status=status.HTTP_400_BAD_REQUEST)

        return JsonResponse({"success": True, "message": "Report Configuration deleted"}, status=status.HTTP_204_NO_CONTENT)
