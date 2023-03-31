# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import AnalysisPropertyView
from seed.serializers.analysis_property_views import (
    AnalysisPropertyViewSerializer
)
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper


class AnalysisPropertyViewViewSet(viewsets.ViewSet, OrgMixin):
    serializer_class = AnalysisPropertyViewSerializer
    model = AnalysisPropertyView

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request, analysis_pk):
        organization_id = int(self.get_organization(request))
        try:
            views_queryset = AnalysisPropertyView.objects.filter(analysis=analysis_pk, analysis__organization_id=organization_id)
        except AnalysisPropertyView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis doesn't exist in this organization."
            }, status=HTTP_409_CONFLICT)

        serialized_views = []
        property_views_by_apv_id = AnalysisPropertyView.get_property_views(views_queryset)
        for view in views_queryset:
            serialized_view = AnalysisPropertyViewSerializer(view).data
            serialized_views.append(serialized_view)

        return JsonResponse({
            'status': 'success',
            'views': serialized_views,
            'original_views': {
                apv_id: property_view.id if property_view is not None else None
                for apv_id, property_view in property_views_by_apv_id.items()
            }
        })

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, analysis_pk, pk):
        organization_id = int(self.get_organization(request))
        try:
            view = AnalysisPropertyView.objects.get(id=pk, analysis=analysis_pk, analysis__organization_id=organization_id)
        except AnalysisPropertyView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis property view doesn't exist in this organization and/or analysis."
            }, status=HTTP_409_CONFLICT)

        property_view_by_apv_id = AnalysisPropertyView.get_property_views([view])
        original_view = property_view_by_apv_id[view.id]

        return JsonResponse({
            'status': 'success',
            'view': AnalysisPropertyViewSerializer(view).data,
            'original_view': original_view.id if original_view is not None else None
        })
