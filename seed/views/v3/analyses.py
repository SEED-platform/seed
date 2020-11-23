# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from drf_yasg.utils import swagger_auto_schema
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view

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
            AutoSchemaHelper.query_integer_field('property_id', True, 'Property ID'),
        ]
    )
    @require_organization_id_class
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    def list(self, request):
        organization_id = request.query_params.get('organization_id', None)
        property_id = request.query_params.get('property_id', None)
        analyses = Analysis.objects.filter(user__default_organization=organization_id)
        serializedData = AnalysisSerializer(analyses, many=True).data

        return JsonResponse({
            'status': 'success',
            'analyses': serializedData,
        })
