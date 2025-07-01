"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request, require_organization_id
from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm
from seed.models import AnalysisPropertyView, PropertyView
from seed.serializers.analysis_property_views import AnalysisPropertyViewSerializer
from seed.utils.api import OrgMixin, api_endpoint
from seed.utils.api_schema import AutoSchemaHelper


class AnalysisPropertyViewViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisPropertyViewSerializer
    model = AnalysisPropertyView

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
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

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
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
