"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.conf import settings
from django.db.models import F
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from seed.analysis_pipelines.better.client import BETTERClient
from seed.analysis_pipelines.pipeline import AnalysisPipeline, AnalysisPipelineError
from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import (
    Analysis,
    AnalysisEvent,
    AnalysisPropertyView,
    Column,
    Cycle,
    Organization,
    PropertyState,
    PropertyView,
    TaxLotState,
    TaxLotView,
)
from seed.models.columns import EXCLUDED_API_FIELDS
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper

logger = logging.getLogger(__name__)


class CreateAnalysisSerializer(AnalysisSerializer):
    property_view_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    access_level_instance_id = serializers.IntegerField(allow_null=False, required=True)

    class Meta:
        model = Analysis
        fields = ["name", "service", "configuration", "property_view_ids", "access_level_instance_id"]
        # `name` has a model default of None, but `create` requires it
        extra_kwargs = {"name": {"required": True}}

    def create(self, validated_data):
        return Analysis.objects.create(
            name=validated_data["name"],
            service=validated_data["service"],
            configuration=validated_data.get("configuration", {}),
            user_id=validated_data["user_id"],
            organization_id=validated_data["organization_id"],
            access_level_instance_id=validated_data["access_level_instance_id"],
        )


# The serializers below are only used to document responses
class AnalysisHighlightSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.JSONField()


class AnalysisDetailSerializer(AnalysisSerializer):
    number_of_analysis_property_views = serializers.IntegerField()
    views = serializers.ListField(child=serializers.IntegerField(), help_text="AnalysisPropertyView IDs")
    cycles = serializers.ListField(child=serializers.IntegerField(), help_text="Cycle IDs")
    highlights = AnalysisHighlightSerializer(many=True)


class AnalysisListOutputFileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    content_type = serializers.CharField()
    file = serializers.CharField(help_text="Path of the file on the server")


class AnalysisListPropertyViewSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_name = serializers.CharField(allow_null=True)
    analysis = serializers.IntegerField()
    property = serializers.IntegerField(allow_null=True)
    cycle = serializers.IntegerField()
    property_state = serializers.IntegerField(allow_null=True)
    output_files = AnalysisListOutputFileSerializer(many=True)


@extend_schema_serializer(many=False)
class AnalysisListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    analyses = AnalysisDetailSerializer(many=True)
    views = AnalysisListPropertyViewSerializer(
        many=True,
        required=False,
        help_text="AnalysisPropertyViews of the listed analyses; omitted if there are none or include_views is false",
    )
    original_views = serializers.DictField(
        child=serializers.IntegerField(allow_null=True),
        required=False,
        help_text="Original PropertyView ID (or null) keyed by AnalysisPropertyView ID; omitted along with `views`",
    )


class AnalysisRetrieveResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    analysis = AnalysisDetailSerializer()


analysis_progress_response_schema = AutoSchemaHelper.schema_factory(
    {"status": "string", "progress_key": "string", "progress": "object"}, required=["status", "progress_key", "progress"]
)
success_response_schema = AutoSchemaHelper.schema_factory({"status": "string"}, required=["status"])
analysis_detail_parameters = [AutoSchemaHelper.query_org_id_field(), AutoSchemaHelper.path_id_field("Analysis ID")]


class AnalysisViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisSerializer
    model = Analysis

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_boolean_field(
                name="start_analysis",
                required=False,
                description="If true, immediately start running the analysis after creation. Defaults to false.",
            ),
        ],
        request={"application/json": CreateAnalysisSerializer},
        responses={200: analysis_progress_response_schema},
        description="Create an analysis of the given property views, which must be within the analysis's access level instance.",
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(body_ali_id="access_level_instance_id"),
        ]
    )
    def create(self, request):
        serializer = CreateAnalysisSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({"status": "error", "message": "Bad request", "errors": serializer.errors})
        if serializer.validated_data["service"] == Analysis.BETTER and not settings.SEED_BETTER_ENABLED:
            return JsonResponse({"status": "error", "message": "BETTER is disabled on this deployment"}, status=HTTP_409_CONFLICT)

        # existing property views must be in the org and within the analysis's access level instance; IDs that
        # don't exist are reported as analysis messages by the pipeline
        property_view_ids = serializer.validated_data["property_view_ids"]
        analysis_ali = AccessLevelInstance.objects.get(pk=serializer.validated_data["access_level_instance_id"])
        property_views = PropertyView.objects.filter(id__in=property_view_ids)
        if property_views.exclude(
            property__organization_id=self.get_organization(request),
            property__access_level_instance__lft__gte=analysis_ali.lft,
            property__access_level_instance__rgt__lte=analysis_ali.rgt,
        ).exists():
            return JsonResponse({"status": "error", "message": "No such resource."}, status=status.HTTP_404_NOT_FOUND)

        analysis = serializer.save(user_id=request.user.id, organization_id=self.get_organization(request))

        # create events
        for property_view in property_views:
            event = AnalysisEvent.objects.create(property_id=property_view.property_id, cycle_id=property_view.cycle_id, analysis=analysis)

            event.save()

        pipeline = AnalysisPipeline.factory(analysis)
        try:
            progress_data = pipeline.prepare_analysis(
                property_view_ids,
                start_analysis=request.query_params.get("start_analysis", "").lower() in serializers.BooleanField.TRUE_VALUES,
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

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_boolean_field(
                "include_views", False, "Include the AnalysisPropertyViews of the listed analyses (`true` or `false`). Defaults to true."
            ),
        ],
        responses={200: AnalysisListResponseSerializer},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
        ]
    )
    def list(self, request):
        organization_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)
        include_views = request.query_params.get("include_views", "true").lower() in serializers.BooleanField.TRUE_VALUES

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

            views_queryset = AnalysisPropertyView.objects.filter(analysis__in=analyses_queryset).order_by("-id")
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

    @extend_schema(parameters=analysis_detail_parameters, responses={200: AnalysisRetrieveResponseSerializer})
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="pk"),
        ]
    )
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

    @extend_schema(parameters=analysis_detail_parameters, request=None, responses={200: analysis_progress_response_schema})
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="pk"),
        ]
    )
    @action(detail=True, methods=["post"])
    def start(self, request, pk):
        organization_id = int(self.get_organization(request))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
            if analysis.service == Analysis.BETTER and not settings.SEED_BETTER_ENABLED:
                return JsonResponse({"status": "error", "message": "BETTER is disabled on this deployment"}, status=HTTP_409_CONFLICT)
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

    @extend_schema(parameters=analysis_detail_parameters, request=None, responses={200: success_response_schema})
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="pk"),
        ]
    )
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

    @extend_schema(parameters=analysis_detail_parameters, responses={200: success_response_schema})
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="pk"),
        ]
    )
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

    @extend_schema(
        parameters=analysis_detail_parameters,
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "progress_key": "string"},
                description="`progress_key` is null if the analysis has no progress data",
            )
        },
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="pk"),
        ]
    )
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

    @extend_schema(
        parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field("cycle_id", True, "Cycle ID"),
        ],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {
                    "status": "string",
                    "total_records": "integer",
                    "number_extra_data_fields": "integer",
                    "total_sqft": "number",
                    "column_settings fields and counts": "object",
                },
                description="`column_settings fields and counts` maps each property column name to its number of non-null values",
            )
        },
        description="Summarize the properties in a cycle that are within the user's access level instance.",
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_viewer"),
        ]
    )
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
        state_ids = PropertyView.objects.filter(
            property__organization_id=org_id,
            cycle_id=cycle_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).values_list("state_id", flat=True)

        if not state_ids:
            return JsonResponse({"success": False, "message": "No properties found for the given cycle"}, status=status.HTTP_404_NOT_FOUND)

        columns = (
            Column.objects.filter(organization_id=org_id, derived_column=None, table_name="PropertyState")
            .exclude(column_name__in=EXCLUDED_API_FIELDS)
            .only("is_extra_data", "column_name")
        )

        extra_data_columns = [c.column_name for c in columns if c.is_extra_data]
        num_of_nonnulls_by_column_name = Column.get_num_of_nonnulls_by_column_name(state_ids, PropertyState, columns)

        gfa_list = PropertyState.objects.filter(id__in=state_ids).values_list("gross_floor_area", flat=True)

        return JsonResponse(
            {
                "status": "success",
                "total_records": len(state_ids),
                "number_extra_data_fields": len(extra_data_columns),
                "total_sqft": sum([x.magnitude for x in gfa_list if x is not None]) if any(x is not None for x in gfa_list) else 0,
                "column_settings fields and counts": num_of_nonnulls_by_column_name,
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: AutoSchemaHelper.schema_factory(
                {"status": "string", "columns": ["object"]},
                description="`columns` are serialized columns, with `shared_field_type` renamed to `sharedFieldType`",
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
    @action(detail=False, methods=["get"])
    def used_columns(self, request):
        """Get all property and taxlot columns that have data in them for an org"""
        org_id = self.get_organization(request)
        access_level_instance = AccessLevelInstance.objects.get(pk=self.request.access_level_instance_id)

        num_of_nonnulls_by_column_name = {}
        tnum_of_nonnulls_by_column_name = {}

        columns = Column.objects.none()
        tcolumns = Column.objects.none()

        # Properties
        state_ids = PropertyView.objects.filter(
            property__organization_id=org_id,
            property__access_level_instance__lft__gte=access_level_instance.lft,
            property__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).values_list("state_id", flat=True)

        if state_ids:
            columns = Column.objects.filter(organization_id=org_id, derived_column=None, table_name="PropertyState").exclude(
                column_name__in=EXCLUDED_API_FIELDS
            )

            num_of_nonnulls_by_column_name = Column.get_num_of_nonnulls_by_column_name(state_ids, PropertyState, columns)

        # Taxlots
        tstate_ids = TaxLotView.objects.filter(
            taxlot__organization_id=org_id,
            taxlot__access_level_instance__lft__gte=access_level_instance.lft,
            taxlot__access_level_instance__rgt__lte=access_level_instance.rgt,
        ).values_list("state_id", flat=True)

        # add non-null counts for extra_data columns
        if tstate_ids:
            tcolumns = Column.objects.filter(organization_id=org_id, derived_column=None, table_name="TaxLotState").exclude(
                column_name__in=EXCLUDED_API_FIELDS
            )
            tnum_of_nonnulls_by_column_name = Column.get_num_of_nonnulls_by_column_name(tstate_ids, TaxLotState, tcolumns)

        # properties and taxlots together
        num_of_nonnulls_by_table = {"PropertyState": num_of_nonnulls_by_column_name, "TaxLotState": tnum_of_nonnulls_by_column_name}
        columns = columns | tcolumns

        # keep only non-zero columns (return full columns)
        columns_to_return = [c for c in columns if num_of_nonnulls_by_table[c.table_name].get(c.column_name)]
        # remove "excluded columns that shouldn't be returned":
        columns_to_return = [c for c in columns_to_return if c.column_name not in Column.COLUMN_EXCLUDE_FIELDS]

        # serialize results
        from seed.serializers.columns import ColumnSerializer

        final_columns = ColumnSerializer(columns_to_return, many=True).data
        # rename shared_field
        for c in final_columns:
            c["sharedFieldType"] = c["shared_field_type"]
            del c["shared_field_type"]
            if not c["display_name"]:
                c["display_name"] = c["column_name"]

        return JsonResponse({"status": "success", "columns": final_columns})

    @extend_schema(
        parameters=[AutoSchemaHelper.query_string_field("better_token", True, "BETTER API token")],
        responses={200: AutoSchemaHelper.schema_factory({"token": "string", "validity": "boolean"})},
    )
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
        ]
    )
    @action(detail=False, methods=["get"])
    def verify_better_token(self, request):
        """Check the validity of a BETTER API token"""
        if not settings.SEED_BETTER_ENABLED:
            return JsonResponse({"status": "error", "message": "BETTER is disabled on this deployment"}, status=HTTP_409_CONFLICT)
        better_token = request.query_params.get("better_token")
        client = BETTERClient(better_token)
        validity, message = client.token_is_valid()
        if message:
            return JsonResponse({"status": "error", "message": message}, status=HTTP_400_BAD_REQUEST)
        return JsonResponse({"token": better_token, "validity": validity})
