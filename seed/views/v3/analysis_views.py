"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import serializers, viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import AnalysisPropertyView, PropertyView
from seed.serializers.analysis_property_views import AnalysisPropertyViewSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper


# The serializers below are only used to document responses
@extend_schema_serializer(many=False)
class AnalysisPropertyViewListResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    views = AnalysisPropertyViewSerializer(many=True)
    original_views = serializers.DictField(
        child=serializers.IntegerField(allow_null=True), help_text="Original PropertyView ID (or null) keyed by AnalysisPropertyView ID"
    )


class AnalysisPropertyViewRetrieveResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    view = AnalysisPropertyViewSerializer()
    original_view = serializers.IntegerField(allow_null=True, help_text="Original PropertyView ID")


@extend_schema(parameters=[AutoSchemaHelper.query_org_id_field(), AutoSchemaHelper.path_id_field("Analysis ID", name="analysis_pk")])
class AnalysisPropertyViewViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisPropertyViewSerializer
    model = AnalysisPropertyView

    @extend_schema(responses={200: AnalysisPropertyViewListResponseSerializer})
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="analysis_pk"),
        ]
    )
    def list(self, request, analysis_pk):
        organization_id = int(self.get_organization(request))
        try:
            views_queryset = AnalysisPropertyView.objects.filter(analysis=analysis_pk, analysis__organization_id=organization_id)
        except AnalysisPropertyView.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis doesn't exist in this organization."}, status=HTTP_409_CONFLICT
            )

        serialized_views = []
        property_views_by_apv_id = AnalysisPropertyView.get_property_views(views_queryset)
        for view in views_queryset:
            serialized_view = AnalysisPropertyViewSerializer(view).data
            serialized_views.append(serialized_view)

        return JsonResponse(
            {
                "status": "success",
                "views": serialized_views,
                "original_views": {
                    apv_id: property_view.id if property_view is not None else None
                    for apv_id, property_view in property_views_by_apv_id.items()
                },
            }
        )

    @extend_schema(
        parameters=[AutoSchemaHelper.path_id_field("AnalysisPropertyView ID")],
        responses={200: AnalysisPropertyViewRetrieveResponseSerializer},
    )
    @method_decorator(
        [
            require_organization_id,
            api_endpoint,
            ajax_request,
            has_perm("requires_member"),
            has_hierarchy_access(analysis_id_kwarg="analysis_pk"),
        ]
    )
    def retrieve(self, request, analysis_pk, pk):
        organization_id = int(self.get_organization(request))
        try:
            view = AnalysisPropertyView.objects.get(id=pk, analysis=analysis_pk, analysis__organization_id=organization_id)
        except AnalysisPropertyView.DoesNotExist:
            return JsonResponse(
                {"status": "error", "message": "Requested analysis property view doesn't exist in this organization and/or analysis."},
                status=HTTP_409_CONFLICT,
            )

        original_view = PropertyView.objects.filter(property=view.property, cycle=view.cycle).first()

        return JsonResponse(
            {
                "status": "success",
                "view": AnalysisPropertyViewSerializer(view).data,
                "original_view": original_view.id if original_view is not None else None,
            }
        )
