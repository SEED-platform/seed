# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.http import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from seed.audit_template.audit_template import AuditTemplate
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper


class AuditTemplateViewSet(viewsets.ViewSet, OrgMixin):

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def get_building_xml(self, request, pk):
        at = AuditTemplate(self.get_organization(self.request))
        response, message = at.get_building(pk)
        if response is None:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)
        return HttpResponse(response.text)
    
    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['PUT'])
    def batch_get_building_xml(self, request):
        properties = request.data
        cycle_id = request.query_params.get('cycle_id')
        at = AuditTemplate(self.get_organization(self.request))
        result = at.batch_get_building_xml(cycle_id, properties)
        # response, message = result.get()
        response = result
        message = ''
        if response is None:
            return JsonResponse({
            'success': False,
            'message': message
        }, status=400)
        return JsonResponse(response)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=False, methods=['GET'])
    def get_buildings(self, request):
        cycle_id = self.request.query_params.get('cycle_id')
        if not cycle_id:
            return JsonResponse({
                'success': False, 
                'message': 'Missing Cycle ID'
            })
        at = AuditTemplate(self.get_organization(self.request))
        result = at.get_buildings(cycle_id)
        response, message = result.get()
        if response is None:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)
        return HttpResponse(response)
