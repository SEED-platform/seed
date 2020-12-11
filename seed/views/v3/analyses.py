# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from drf_yasg.utils import swagger_auto_schema
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Analysis, AnalysisPropertyView
from seed.serializers.analyses import AnalysisSerializer
from seed.serializers.analysis_property_views import AnalysisPropertyViewSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper


class AnalysisViewSet(viewsets.ViewSet):
    serializer_class = AnalysisSerializer
    model = Analysis

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field('property_id', False, 'Property ID')
        ]
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request):
        organization_id = request.query_params.get('organization_id', None)
        property_id = request.query_params.get('property_id', None)
        analyses = []
        if property_id is not None:
            analyses_queryset = Analysis.objects.filter(organization=organization_id, analysispropertyview__property=property_id).distinct()
        else:
            analyses_queryset = Analysis.objects.filter(organization=organization_id)
        for analysis in analyses_queryset:
            property_view_info = analysis.get_property_view_info(property_id)
            serialized_analysis = AnalysisSerializer(analysis).data
            serialized_analysis.update(property_view_info)
            analyses.append(serialized_analysis)

        return JsonResponse({
            'status': 'success',
            'analyses': analyses
        })

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, pk):
        organization_id = int(request.query_params.get('organization_id', 0))
        try:
            analysis = Analysis.objects.get(id=pk, organization_id=organization_id)
        except Analysis.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis doesn't exist in this organization."
            }, status=HTTP_409_CONFLICT)
        serialized_analysis = AnalysisSerializer(analysis).data
        property_view_info = analysis.get_property_view_info()
        serialized_analysis.update(property_view_info)

        return JsonResponse({
            'status': 'success',
            'analysis': serialized_analysis
        })


class AnalysisPropertyViewViewSet(viewsets.ViewSet):
    serializer_class = AnalysisPropertyViewSerializer
    model = AnalysisPropertyView

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field('property_id', False, 'Property ID')
        ]
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request, analysis_pk):
        organization_id = int(request.query_params.get('organization_id', 0))
        try:
            views_queryset = AnalysisPropertyView.objects.filter(analysis=analysis_pk, analysis__organization_id=organization_id)
        except AnalysisPropertyView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis doesn't exist in this organization."
            }, status=HTTP_409_CONFLICT)
        views = []
        for view in views_queryset:
            serialized_view = AnalysisPropertyViewSerializer(view).data
            views.append(serialized_view)

        return JsonResponse({
            'status': 'success',
            'views': views
        })

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(True)])
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def retrieve(self, request, analysis_pk, pk):
        organization_id = int(request.query_params.get('organization_id', 0))
        try:
            view = AnalysisPropertyView.objects.get(id=pk, analysis=analysis_pk, analysis__organization_id=organization_id)
        except AnalysisPropertyView.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis property view doesn't exist in this organization and/or analysis."
            }, status=HTTP_409_CONFLICT)
        serialized_view = AnalysisPropertyViewSerializer(view).data

        return JsonResponse({
            'status': 'success',
            'view': serialized_view
        })
