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
from seed.models import Analysis
from seed.serializers.analyses import AnalysisSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper


class AnalysisViewSet(viewsets.ViewSet):
    serializer_class = AnalysisSerializer
    model = Analysis

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
            property_view_info = analysis.getPropertyViewInfo(property_id)
            if property_id is not None and property_view_info["number_of_analysis_property_views"] < 1:
                continue
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
    def retrieve(self, request, pk):
        organization_id = int(request.query_params.get('organization_id', 0))
        analysis = Analysis.objects.get(id=pk)
        if analysis.organization_id != organization_id:

            return JsonResponse({
                'status': 'error',
                'message': "Requested analysis doesn't exist in this organization."
            }, status=HTTP_409_CONFLICT)
        serialized_analysis = AnalysisSerializer(analysis).data
        property_view_info = analysis.getPropertyViewInfo()
        serialized_analysis.update(property_view_info)

        return JsonResponse({
            'status': 'success',
            'analysis': serialized_analysis
        })
