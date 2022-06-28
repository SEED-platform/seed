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

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def get_building_xml(self, request, pk):
        org_id = self.get_organization(self.request)
        org = Organization.objects.get(pk=org_id)
        at_api_token = org.at_api_token
        if not at_api_token:
            return JsonResponse({
                'success': False,
                'message': "Organization's `at_api_token` is either missing or invalid"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        at = AuditTemplate(at_api_token)
        response, message = at.get_building(pk)
        if not response:
            return JsonResponse({
                'success': False,
                'message': message
            })
        return JsonResponse({
            'success': True,
            'data': response.text
        })

    # @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field(),
    #     AutoSchemaHelper.query_integer_field(
    #         'property_state_id',
    #         required=True,
    #         description='Audit Template Organization Token'
    #     )])
    # @has_perm_class('can_modify_data')
    # @action(detail=True, methods=['POST'])
    # def update_property(self, request, pk):
        # org_id = self.get_organization(self.request)
        # org = Organization.objects.get(pk=org_id)
        # at_api_token = org.at_api_token
        # if not at_api_token:
        #     return JsonResponse({
        #         'success': False,
        #         'message': "Organization's `at_api_token` is either missing or invalid"
        #     }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # property_state_id = request.query_params.get('property_state_id', None)
        # if not property_state_id:
        #     return JsonResponse({
        #         'success': False,
        #         'message': 'Property State id is not defined'
        #     })

        # at_building_xml = self._get_building_xml(at_api_token, pk)
        # todo: update property here using `at_building_xml` and `property_state_id`

    @swagger_auto_schema(manual_parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.query_integer_field(
            'org_token',
            required=True,
            description='Audit Template Organization Token'
        ),
        AutoSchemaHelper.query_integer_field(
            'email',
            required=True,
            description='Audit Template Email'
        ),
        AutoSchemaHelper.query_integer_field(
            'password',
            required=True,
            description='Audit Template Password'
        )])
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['GET'])
    def get_api_token(self, request):
        org_token = request.query_params.get('organization_token', None)
        if not org_token:
            return JsonResponse({
                'success': False,
                'message': 'Audit Template organization token is not defined'
            })
        email = request.query_params.get('email', None)
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Audit Template email is not defined'
            })
        password = request.query_params.get('password', None)
        if not password:
            return JsonResponse({
                'success': False,
                'message': 'Audit Template password is not defined'
            })

        at = AuditTemplate(None)
        token, message = at.get_api_token(org_token, email, password)
        if not token:
            return JsonResponse({
                'success': False,
                'message': message
            })

        org_id = self.get_organization(self.request)
        org = Organization.objects.get(pk=org_id)
        org.at_api_token = token
        org.save()
        return JsonResponse({
            'success': True,
            'data': token
        })
