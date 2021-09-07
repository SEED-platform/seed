# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.status import HTTP_409_CONFLICT

from seed.decorators import ajax_request_class, require_organization_id_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import AnalysisPropertyView, PropertyView
from seed.serializers.analysis_property_views import AnalysisPropertyViewSerializer
from seed.utils.api import api_endpoint_class, OrgMixin
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
        original_views = {}
        for view in views_queryset:
            serialized_view = AnalysisPropertyViewSerializer(view).data
            serialized_views.append(serialized_view)
            property_view_query = Q(property=view.property) & Q(cycle=view.cycle)
            property_views_by_property_cycle_id = {
                (pv.property.id, pv.cycle.id): pv
                for pv in PropertyView.objects.filter(property_view_query).prefetch_related('state')
            }
            original_views[view.id] = property_views_by_property_cycle_id[(view.property.id, view.cycle.id)].id

        return JsonResponse({
            'status': 'success',
            'views': serialized_views,
            'original_views': original_views
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
        property_view_query = Q(property=view.property) & Q(cycle=view.cycle)
        property_views_by_property_cycle_id = {
            (pv.property.id, pv.cycle.id): pv
            for pv in PropertyView.objects.filter(property_view_query).prefetch_related('state')
        }
        original_view = property_views_by_property_cycle_id[(view.property.id, view.cycle.id)].id

        return JsonResponse({
            'status': 'success',
            'view': AnalysisPropertyViewSerializer(view).data,
            'original_view': original_view
        })
