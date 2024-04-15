# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging

from django.db.models import F
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_409_CONFLICT

from seed.analysis_pipelines.better.client import BETTERClient
from seed.analysis_pipelines.pipeline import AnalysisPipeline, AnalysisPipelineError
from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import Analysis, AnalysisEvent, AnalysisPropertyView, Column, Cycle, Organization, PropertyState, PropertyView
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper

logger = logging.getLogger(__name__)


class CreateAnalysisSerializer(AnalysisSerializer):
    property_view_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    access_level_instance_id = serializers.IntegerField(allow_null=False, required=True)

    class Meta:
        model = Analysis
        fields = ["name", "service", "configuration", "property_view_ids", "access_level_instance_id"]

    def create(self, validated_data):
        return Analysis.objects.create(
            name=validated_data["name"],
            service=validated_data["service"],
            configuration=validated_data.get("configuration", {}),
            user_id=validated_data["user_id"],
            organization_id=validated_data["organization_id"],
            access_level_instance_id=validated_data["access_level_instance_id"],
        )


class AnalysisViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisSerializer
    model = Analysis

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_boolean_field(
                name="start_analysis",
                required=True,
                description="If true, immediately start running the analysis after creation. Defaults to false.",
            ),
        ],
        request_body=CreateAnalysisSerializer,
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(body_ali_id="access_level_instance_id")
    def create(self, request):
        serializer = CreateAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({"status": "error", "message": "Bad request", "errors": serializer.errors})

        analysis = serializer.save(user_id=request.user.id, organization_id=self.get_organization(request))

        # create events
        property_views = PropertyView.objects.filter(id__in=request.data["property_view_ids"])
        for property_view in property_views:
            event = AnalysisEvent.objects.create(property_id=property_view.property_id, cycle_id=property_view.cycle_id, analysis=analysis)

            event.save()

        pipeline = AnalysisPipeline.factory(analysis)
        try:
            progress_data = pipeline.prepare_analysis(
                serializer.validated_data["property_view_ids"], start_analysis=request.query_params.get("start_analysis", False)
            )
            return JsonResponse(
                {
                    "status": "success",
                    "progress_key": progress_data["progress_key"],
                    "progress": progress_data,
                }
            )
        except AnalysisPipelineError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=HTTP_409_CONFLICT)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field("property_id", False, "Property ID"),
        ]
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        include_views = json.loads(request.query_params.get("include_views", "true"))

        analyses = []
        analyses_queryset = Analysis.objects.filter(
            organization=organization_id,
            access_level_instance__lft__gte=access_level_instance.lft,
            access_level_instance__rgt__lte=access_level_instance.rgt,
        ).order_by("-id")

        for analysis in analyses_queryset:
            serialized_analysis = AnalysisSerializer(analysis).data
            serialized_analysis.update(analysis.get_property_view_info())
            serialized_analysis.update({"highlights": analysis.get_highlights()})
            analyses.append(serialized_analysis)

        results = {"status": "success", "analyses": analyses}

        if analyses and include_views:
            org = Organization.objects.get(pk=organization_id)
            display_column = Column.objects.filter(organization=org, column_name=org.property_display_field).first()
            display_column_field = display_column.column_name
            if display_column.is_extra_data:
                display_column_field = "extra_data__" + display_column_field

            views_queryset = AnalysisPropertyView.objects.filter(analysis__organization_id=organization_id).order_by("-id")
            views_queryset = views_queryset.annotate(display_name=F(f"property_state__{display_column_field}")).prefetch_related(
                "analysisoutputfile_set"
            )
            property_views_by_apv_id = AnalysisPropertyView.get_property_views(views_queryset)

            results["views"] = [
                {
                    "id": view.id,
                    "display_name": view.display_name,
                    "analysis": view.analysis_id,
                    "property": view.property_id,
                    "cycle": view.cycle_id,
                    "property_state": view.property_state_id,
                    "output_files": [
                        {"id": output_file.id, "content_type": output_file.content_type, "file": output_file.file.path}
                        for output_file in view.analysisoutputfile_set.all()
                    ],
                }
                for view in views_queryset
            ]
            results["original_views"] = {
                apv_id: property_view.id if property_view is not None else None
                for apv_id, property_view in property_views_by_apv_id.items()
            }

        return JsonResponse(results)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(analysis_id_kwarg="pk")
    def retrieve(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
        except Analysis.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis doesn't exist in this organization."}, status=HTTP_409_CONFLICT
            )
        serialized_analysis = AnalysisSerializer(analysis).data
        serialized_analysis.update(analysis.get_property_view_info())
        serialized_analysis.update({"highlights": analysis.get_highlights()})

        return JsonResponse({"status": "success", "analysis": serialized_analysis})

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @action(detail=True, methods=["post"])
    @has_hierarchy_access(analysis_id_kwarg="pk")
    def start(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            progress_data = pipeline.start_analysis()
            return JsonResponse(
                {
                    "status": "success",
                    "progress_key": progress_data["progress_key"],
                    "progress": progress_data,
                }
            )
        except Analysis.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis doesn't exist in this organization."}, status=HTTP_409_CONFLICT
            )
        except AnalysisPipelineError as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=HTTP_409_CONFLICT)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(analysis_id_kwarg="pk")
    @action(detail=True, methods=["post"])
    def stop(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            pipeline.stop()
            return JsonResponse(
                {
                    "status": "success",
                }
            )
        except Analysis.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis doesn't exist in this organization."}, status=HTTP_409_CONFLICT
            )

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(analysis_id_kwarg="pk")
    def destroy(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            pipeline.delete()
            return JsonResponse(
                {
                    "status": "success",
                }
            )
        except Analysis.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis doesn't exist in this organization."}, status=HTTP_409_CONFLICT
            )

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_member")
    @has_hierarchy_access(analysis_id_kwarg="pk")
    @action(detail=True, methods=["get"])
    def progress_key(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            pipeline = AnalysisPipeline.factory(analysis)
            progress_data = pipeline.get_progress_data(analysis)
            progress_key = progress_data.key if progress_data is not None else None
            return JsonResponse(
                {
                    "status": "success",
                    # NOTE: intentionally *not* returning the actual progress here b/c then
                    # folks will poll this endpoint which is less efficient than using
                    # the /progress/<key> endpoint
                    "progress_key": progress_key,
                }
            )
        except Analysis.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis doesn't exist in this organization."}, status=HTTP_409_CONFLICT
            )

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class("requires_viewer")
    @action(detail=False, methods=["get"])
    def stats(self, request):
        org_id = self.get_organization(request)
        cycle_id = request.query_params.get("cycle_id")

        if not cycle_id:
            return JsonResponse({"success": False, "message": "cycle_id parameter is missing"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            Cycle.objects.get(id=cycle_id, organization_id=org_id)
        except Cycle.DoesNotExist:
            return JsonResponse({"success": False, "message": "Cycle does not exist"}, status=status.HTTP_404_NOT_FOUND)

        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        views = PropertyView.objects.filter(
            property__organization_id=org_id,
            cycle_id=cycle_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        )
        states = PropertyState.objects.filter(id__in=views.values_list("state_id", flat=True))
        columns = Column.objects.filter(organization_id=org_id, derived_column=None, table_name="PropertyState").only(
            "is_extra_data", "column_name"
        )

        num_of_nonnulls_by_column_name = {}
        for column in columns:
            name = column.column_name
            if column.is_extra_data:
                count = states.filter(extra_data__has_key=name).exclude(**{f"extra_data__{name}": None}).count()
            else:
                count = states.exclude(**{name: None}).count()

            num_of_nonnulls_by_column_name[name] = count

        return JsonResponse(
            {
                "status": "success",
                "total_records": views.count(),
                "number_extra_data_fields": columns.filter(is_extra_data=True).count(),
                "column_settings fields and counts": num_of_nonnulls_by_column_name,
            }
        )

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @action(detail=False, methods=["get"])
    def verify_better_token(self, request):
        """Check the validity of organization's BETTER API token"""
        organization_id = int(self.get_organization(request))
        organization = Organization.objects.get(pk=organization_id)
        client = BETTERClient(organization.better_analysis_api_key)
        validity = client.token_is_valid()
        return JsonResponse({"token": organization.better_analysis_api_key, "validity": validity})
