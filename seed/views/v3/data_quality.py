# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import csv

from celery.utils.log import get_task_logger
from django.http import JsonResponse, HttpResponse
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from unidecode import unidecode

from seed.data_importer.tasks import do_checks
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    Organization,
)
from seed.models.data_quality import (
    Rule,
    DataQualityCheck,
)
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.cache import get_cache_raw

logger = get_task_logger(__name__)


class RulesSubSerializer(serializers.Serializer):
    field = serializers.CharField(max_length=100)
    severity = serializers.CharField(max_length=100)


class RulesSubSerializerB(serializers.Serializer):
    field = serializers.CharField(max_length=100)
    enabled = serializers.BooleanField()
    data_type = serializers.CharField(max_length=100)
    min = serializers.FloatField()
    max = serializers.FloatField()
    severity = serializers.CharField(max_length=100)
    units = serializers.CharField(max_length=100)


class RulesIntermediateSerializer(serializers.Serializer):
    missing_matching_field = RulesSubSerializer(many=True)
    missing_values = RulesSubSerializer(many=True)
    in_range_checking = RulesSubSerializerB(many=True)


class RulesSerializer(serializers.Serializer):
    data_quality_rules = RulesIntermediateSerializer()


def _get_js_rule_type(data_type):
    """return the JS friendly data type name for the data data_quality rule

    :param data_type: data data_quality rule data type as defined in data_quality.models
    :returns: (string) JS data type name
    """
    return dict(Rule.DATA_TYPES).get(data_type)


def _get_js_rule_severity(severity):
    """return the JS friendly severity name for the data data_quality rule

    :param severity: data data_quality rule severity as defined in data_quality.models
    :returns: (string) JS severity name
    """
    return dict(Rule.SEVERITY).get(severity)


def _get_rule_type_from_js(data_type):
    """return the Rules TYPE from the JS friendly data type

    :param data_type: 'string', 'number', 'date', or 'year'
    :returns: int data type as defined in data_quality.models
    """
    d = {v: k for k, v in dict(Rule.DATA_TYPES).items()}
    return d.get(data_type)


def _get_severity_from_js(severity):
    """return the Rules SEVERITY from the JS friendly severity

    :param severity: 'error', or 'warning'
    :returns: int severity as defined in data_quality.models
    """
    d = {v: k for k, v in dict(Rule.SEVERITY).items()}
    return d.get(severity)


class DataQualitySchema(AutoSchemaHelper):
    def __init__(self, *args):
        super().__init__(*args)

        self.manual_fields = {
            ('POST', 'create'): [
                self.org_id_field(),
                self.body_field(
                    name='data_quality_ids',
                    required=True,
                    description="An object containing IDs of the records to perform data quality checks on. Should contain two keys- property_state_ids and taxlot_state_ids, each of which is an array of appropriate IDs.",
                    params_to_formats={
                        'property_state_ids': 'interger_list',
                        'taxlot_state_ids': 'interger_list'
                    }
                ),
            ],
            ('GET', 'data_quality_rules'): [self.org_id_field()],
            ('PUT', 'reset_all_data_quality_rules'): [self.org_id_field()],
            ('PUT', 'reset_default_data_quality_rules'): [self.org_id_field()],
            ('POST', 'save_data_quality_rules'): [
                self.org_id_field(),
                self.body_field(
                    name='data_quality_rules',
                    required=True,
                    description="Rules information"
                )
            ],
            ('GET', 'results'): [
                self.org_id_field(),
                self.query_integer_field(
                    name='data_quality_id',
                    required=True,
                    description="Task ID created when DataQuality task is created."
                ),
            ],
            ('GET', 'csv'): [
                # This will replace the auto-generated field - adds description.
                self.path_id_field(description="Import file ID or cache key")
            ],
        }


class DataQualityViews(viewsets.ViewSet):
    """
    Handles Data Quality API operations within Inventory backend.
    (1) Post, wait, get…
    (2) Respond with what changed
    """
    swagger_schema = DataQualitySchema

    def create(self, request):
        """
        This API endpoint will create a new cleansing operation process in the background,
        on potentially a subset of properties/taxlots, and return back a query key
        ---
        parameters:
            - name: organization_id
              description: Organization ID
              type: integer
              required: true
              paramType: query
            - name: data_quality_ids
              description: An object containing IDs of the records to perform data quality checks on.
                           Should contain two keys- property_state_ids and taxlot_state_ids, each of which is an array
                           of appropriate IDs.
              required: true
              paramType: body
        type:
            status:
                type: string
                description: success or error
                required: true
        """
        # step 0: retrieving the data
        body = request.data
        property_state_ids = body['property_state_ids']
        taxlot_state_ids = body['taxlot_state_ids']
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        # step 1: validate the check IDs all exist
        # step 2: validate the check IDs all belong to this organization ID
        # step 3: validate the actual user belongs to the passed in org ID
        # step 4: kick off a background task
        return_value = do_checks(organization.id, property_state_ids, taxlot_state_ids)
        # step 5: create a new model instance
        return JsonResponse({
            'num_properties': len(property_state_ids),
            'num_taxlots': len(taxlot_state_ids),
            # TODO #239: Deprecate progress_key from here and just use the 'progess.progress_key'
            'progress_key': return_value['progress_key'],
            'progress': return_value,
        })

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['GET'])
    def csv(self, request, pk):
        """
        Download a csv of the data quality checks by the pk which is the cache_key
        ---
        parameter_strategy: replace
        parameters:
            - name: pk
              description: Import file ID or cache key
              required: true
              paramType: path
        """
        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(pk))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Data Quality Check Results.csv"'

        writer = csv.writer(response)
        if data_quality_results is None:
            writer.writerow(['Error'])
            writer.writerow(['data quality results not found'])
            return response

        writer.writerow(
            ['Table', 'Address Line 1', 'PM Property ID', 'Tax Lot ID', 'Custom ID', 'Field',
             'Applied Label', 'Error Message', 'Severity'])

        for row in data_quality_results:
            for result in row['data_quality_results']:
                writer.writerow([
                    row['data_quality_results'][0]['table_name'],
                    row['address_line_1'],
                    row['pm_property_id'] if 'pm_property_id' in row else None,
                    row['jurisdiction_tax_lot_id'] if 'jurisdiction_tax_lot_id' in row else None,
                    row['custom_id_1'],
                    result['formatted_field'],
                    result.get('label', None),
                    # the detailed_message field can have units which has superscripts/subscripts, so unidecode it!
                    unidecode(result['detailed_message']),
                    result['severity']
                ])

        return response

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['GET'])
    def data_quality_rules(self, request):
        """
        Returns the data_quality rules for an org.
        ---
        parameters:
            - name: organization_id
              description: Organization ID
              type: integer
              required: true
              paramType: query
        type:
            status:
                type: string
                required: true
                description: success or error
            rules:
                type: object
                required: true
                description: An object containing 'properties' and 'taxlots' arrays of rules
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        result = {
            'status': 'success',
            'rules': {
                'properties': [],
                'taxlots': []
            }
        }

        dq = DataQualityCheck.retrieve(organization.id)
        rules = dq.rules.order_by('field', 'severity')
        for rule in rules:
            result['rules'][
                'properties' if rule.table_name == 'PropertyState' else 'taxlots'].append({
                    'field': rule.field,
                    'enabled': rule.enabled,
                    'data_type': _get_js_rule_type(rule.data_type),
                    'rule_type': rule.rule_type,
                    'required': rule.required,
                    'not_null': rule.not_null,
                    'min': rule.min,
                    'max': rule.max,
                    'text_match': rule.text_match,
                    'severity': _get_js_rule_severity(rule.severity),
                    'units': rule.units,
                    'label': rule.status_label_id
                })

        return JsonResponse(result)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['PUT'])
    def reset_all_data_quality_rules(self, request):
        """
        Resets an organization's data data_quality rules
        ---
        parameters:
            - name: organization_id
              description: Organization ID
              type: integer
              required: true
              paramType: query
        type:
            status:
                type: string
                description: success or error
                required: true
            in_range_checking:
                type: array[string]
                required: true
                description: An array of in-range error rules
            missing_matching_field:
                type: array[string]
                required: true
                description: An array of fields to verify existence
            missing_values:
                type: array[string]
                required: true
                description: An array of fields to ignore missing values
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        dq = DataQualityCheck.retrieve(organization.id)
        dq.reset_all_rules()
        return self.data_quality_rules(request)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['PUT'])
    def reset_default_data_quality_rules(self, request):
        """
        Resets an organization's data data_quality rules
        ---
        parameters:
            - name: organization_id
              description: Organization ID
              type: integer
              required: true
              paramType: query
        type:
            status:
                type: string
                description: success or error
                required: true
            in_range_checking:
                type: array[string]
                required: true
                description: An array of in-range error rules
            missing_matching_field:
                type: array[string]
                required: true
                description: An array of fields to verify existence
            missing_values:
                type: array[string]
                required: true
                description: An array of fields to ignore missing values
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        dq = DataQualityCheck.retrieve(organization.id)
        dq.reset_default_rules()
        return self.data_quality_rules(request)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['POST'])
    def save_data_quality_rules(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields.
        The method passes in all the fields again, so it is okay to remove
        all the rules in the db, and just recreate them (albeit inefficient)
        ---
        parameter_strategy: replace
        parameters:
            - name: organization_id
              description: Organization ID
              type: integer
              required: true
              paramType: query
            - name: body
              description: JSON body containing organization rules information
              paramType: body
              pytype: RulesSerializer
              required: true
        type:
            status:
                type: string
                description: success or error
                required: true
            message:
                type: string
                description: error message, if any
                required: true
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        body = request.data
        if body.get('data_quality_rules') is None:
            return JsonResponse({
                'status': 'error',
                'message': 'missing the data_quality_rules'
            }, status=status.HTTP_404_NOT_FOUND)

        posted_rules = body['data_quality_rules']
        updated_rules = []
        for rule in posted_rules['properties']:
            updated_rules.append(
                {
                    'field': rule['field'],
                    'table_name': 'PropertyState',
                    'enabled': rule['enabled'],
                    'data_type': _get_rule_type_from_js(rule['data_type']),
                    'rule_type': rule['rule_type'],
                    'required': rule['required'],
                    'not_null': rule['not_null'],
                    'min': rule['min'],
                    'max': rule['max'],
                    'text_match': rule['text_match'],
                    'severity': _get_severity_from_js(rule['severity']),
                    'units': rule['units'],
                    'status_label_id': rule['label']
                }
            )

        for rule in posted_rules['taxlots']:
            updated_rules.append(
                {
                    'field': rule['field'],
                    'table_name': 'TaxLotState',
                    'enabled': rule['enabled'],
                    'data_type': _get_rule_type_from_js(rule['data_type']),
                    'rule_type': rule['rule_type'],
                    'required': rule['required'],
                    'not_null': rule['not_null'],
                    'min': rule['min'],
                    'max': rule['max'],
                    'text_match': rule['text_match'],
                    'severity': _get_severity_from_js(rule['severity']),
                    'units': rule['units'],
                    'status_label_id': rule['label']
                }
            )

        dq = DataQualityCheck.retrieve(organization.id)
        dq.remove_all_rules()
        for rule in updated_rules:
            if rule['severity'] == Rule.SEVERITY_VALID and rule['status_label_id'] is None:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Label must be assigned when using Valid Data Severity.'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                dq.add_rule(rule)
            except TypeError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': e,
                }, status=status.HTTP_400_BAD_REQUEST)

        return self.data_quality_rules(request)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['GET'])
    def results(self, request):
        """
        Return the result of the data quality based on the ID that was given during the
        creation of the data quality task. Note that it is not related to the object in the
        database, since the results are stored in redis!
        """
        Organization.objects.get(pk=request.query_params['organization_id'])

        data_quality_id = request.query_params['data_quality_id']
        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(data_quality_id))
        return JsonResponse({
            'data': data_quality_results
        })
