# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from drf_yasg.utils import swagger_auto_schema
from django.http import JsonResponse
from rest_framework import viewsets

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Analysis, AnalysisPropertyView
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper


class AnalysisViewSet(viewsets.ViewSet):
    serializer_class = AnalysisSerializer
    model = Analysis

    def add_property_view_info(self, serialized_analysis, analysis_id):
        analysis_property_views = AnalysisPropertyView.objects.filter(analysis=analysis_id)
        serialized_analysis['number_of_analysis_property_views'] = analysis_property_views.count()
        serialized_analysis['cycles'] = list(analysis_property_views.values_list('cycle', flat=True).distinct())
        return serialized_analysis

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(True),
            AutoSchemaHelper.query_integer_field('property_id', True, 'Property ID')
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
        for analysis in Analysis.objects.filter(organization=organization_id):
            if property_id is not None and AnalysisPropertyView.objects.filter(analysis=analysis.id, property=property_id).count() < 1:
                continue
            serialized_analysis = AnalysisSerializer(analysis).data
            serialized_analysis = self.add_property_view_info(serialized_analysis, analysis.id)
            analyses.append(serialized_analysis)

        return JsonResponse({
            'status': 'success',
            'analyses': analyses
        })

    @api_endpoint_class
    @ajax_request_class
    def retrieve(self, request, pk):
        analysis = AnalysisSerializer(Analysis.objects.get(id=pk)).data
        analysis = self.add_property_view_info(analysis, pk)

        return JsonResponse({
            'status': 'success',
            'analysis': analysis
        })
