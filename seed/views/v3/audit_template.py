# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json

from django.http import HttpResponse, JsonResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.decorators import action

from seed.audit_template.audit_template import AuditTemplate
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.models import Cycle
from seed.utils.api import OrgMixin
from seed.utils.api_schema import AutoSchemaHelper


class AuditTemplateViewSet(viewsets.ViewSet, OrgMixin):
    @swagger_auto_schema(manual_parameters=[
        AutoSchemaHelper.query_org_id_field(),
        AutoSchemaHelper.base_field(
            name='id',
            location_attr='IN_PATH',
            type='TYPE_INTEGER',
            required=True,
            description='Audit Template Submission ID.'),
        AutoSchemaHelper.query_string_field('report_format', False, 'Report format Valid values are: xml, pdf. Defaults to pdf.')
    ])
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def get_submission(self, request, pk):
        """
        Fetches a Report Submission (XML or PDF) from Audit Template (only)
        """
        # get report format or default to pdf
        default_report_format = 'pdf'
        report_format = request.query_params.get('report_format', default_report_format)

        valid_file_formats = ['json', 'xml', 'pdf']
        if report_format.lower() not in valid_file_formats:
            message = f"The report_format specified is invalid. Must be one of: {valid_file_formats}."
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)

        # retrieve report
        at = AuditTemplate(self.get_organization(self.request))
        response, message = at.get_submission(pk, report_format)

        # error
        if response is None:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)
        # json
        if report_format.lower() == 'json':
            return JsonResponse(json.loads(response.content))
        # xml
        if report_format.lower() == 'xml':
            return HttpResponse(response.text)
        # pdf
        response2 = HttpResponse(response.content)
        response2.headers["Content-Type"] = 'application/pdf'
        response2.headers["Content-Disposition"] = f'attachment; filename="at_submission_{pk}.pdf"'
        return response2

    @swagger_auto_schema(manual_parameters=[AutoSchemaHelper.query_org_id_field()])
    @has_perm_class('can_view_data')
    @action(detail=True, methods=['GET'])
    def get_building_xml(self, request, pk):
        """
        Fetches a Building XML for an Audit Template property (only)
        """
        at = AuditTemplate(self.get_organization(self.request))
        response, message = at.get_building(pk)
        if response is None:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)
        return HttpResponse(response.text)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle_id',
                required=True,
                description='Cycle ID'
            ),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            [
                {
                    'audit_template_building_id': 'integer',
                    'property_view': 'integer',
                    'email': 'string',
                    'updated_at': 'string',
                }
            ],
        )
    )
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['PUT'])
    def batch_get_building_xml(self, request):
        """
        Fetches Building XMLs for a list of Audit Template properties and updates corresponding PropertyViews.
        The return value is a ProgressData object used to monitor the status of the background task.
        """

        properties = request.data

        valid, message = self.validate_properties(properties)
        if not valid:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)

        org = self.get_organization(request)
        cycle_id = request.query_params.get('cycle_id')

        if not cycle_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing Cycle ID'
            })

        if not Cycle.objects.filter(id=cycle_id, organization=org).exists():
            return JsonResponse({
                'success': False,
                'message': 'Cycle does not exist'
            }, status=404)

        at = AuditTemplate(org)
        progress_data = at.batch_get_building_xml(cycle_id, properties)

        if progress_data is None:
            return JsonResponse({
                'success': False,
                'message': 'Unexpected Error'
            }, status=400)

        return JsonResponse(progress_data)

    def validate_properties(self, properties):
        valid = [bool(properties)]
        for property in properties:
            valid.append(len(property) == 5)
            valid.append(property.get('audit_template_building_id'))
            valid.append(property.get('property_view'))
            valid.append(property.get('email'))
            valid.append(property.get('updated_at'))
            valid.append(property.get('name'))

        if not all(valid):
            return False, "Request data must be structured as: {audit_template_building_id: integer, property_view: integer, email: string, updated_at: date time iso string 'YYYY-MM-DDTHH:MM:SSZ'}"
        else:
            return True, ""

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle_id',
                required=True,
                description='Cycle ID'
            ),
        ]
    )
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['GET'])
    def get_buildings(self, request):
        """
        Fetches all properties associated with the linked Audit Template account via the Audit Template API
        """
        org = self.get_organization(request)
        cycle_id = request.query_params.get('cycle_id')
        if not cycle_id:
            return JsonResponse({
                'success': False,
                'message': 'Missing Cycle ID'
            })

        if not Cycle.objects.filter(id=cycle_id, organization=org).exists():
            return JsonResponse({
                'success': False,
                'message': 'Cycle does not exist'
            }, status=404)

        at = AuditTemplate(org)
        result = at.get_buildings(cycle_id)

        if isinstance(result, tuple):
            return JsonResponse({
                'success': False,
                'message': result[1]
            }, status=200)

        response, message = result.get()
        if response is None:
            return JsonResponse({
                'success': False,
                'message': message
            }, status=400)

        return JsonResponse({
            'success': True,
            'message': response
        }, status=200)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field(),
            AutoSchemaHelper.query_integer_field(
                'cycle_id',
                required=True,
                description='Cycle ID'
            ),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_view_ids': ['integer']
            },
            description='PropertyView IDs to be exported'
        )
    )
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['POST'])
    def batch_export_to_audit_template(self, request):
        """
        Batch exports properties without Audit Template Building IDs to the linked Audit Template.
        SEED properties will be updated with the returned Audit Template Building ID
        """
        property_view_ids = request.data.get('property_view_ids', [])
        at = AuditTemplate(self.get_organization(request))

        progress_data, message = at.batch_export_to_audit_template(property_view_ids)
        if progress_data is None:
            return JsonResponse({
                'success': False,
                'message': message or 'Unexpected Error'
            }, status=400)
        return JsonResponse(progress_data)
    
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_org_id_field()
        ]
    )
    @has_perm_class('can_modify_data')
    @action(detail=False, methods=['PUT'])
    def batch_get_city_submission_xml(self, request):
        """
        Batch import from Audit Template using the submissions endpoint for a given city
        Properties are updated with xmls using custom_id_1 as matching criteria
        """
        import logging
        logging.error('>>> test response')

        city_id = request.data.get('city_id')
        if not city_id:
            return JsonResponse({
                'success': False,
                'message': 'City ID argument required'
            }, status=400)
        
        at = AuditTemplate(self.get_organization(request))
        at.batch_get_city_submission_xml
        

        return JsonResponse({
            'success': True,
            'message': 'test success'
        })
