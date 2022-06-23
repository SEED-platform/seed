# !/usr/bin/env python
# encoding: utf-8

from django.http import JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action

from seed.audit_template.audit_template import AuditTemplate
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.utils.api import OrgMixin, api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper


class AuditTemplateViewSet(viewsets.ViewSet, OrgMixin):


    def get_json(self, pk, detail):
        org_id = self.get_organization(self.request)
        org = Organization.objects.get(pk=org_id)
        at_api_token = org.at_api_token
        if not at_api_token:
            return JsonResponse({
                'success': False,
                'message': "Organization's `at_api_token` is either missing or invalid"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        at = AuditTemplate(at_api_token)
        return at.get_building(pk, detail)

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def get_simple_json(self, request, pk):
        response = self.get_json(pk, False)

        return JsonResponse({
            'success': True,
            'response': response
        })

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def get_detailed_json(self, request, pk):
        response = self.get_json(pk, True)

        return JsonResponse({
            'success': True,
            'response': response
        })
