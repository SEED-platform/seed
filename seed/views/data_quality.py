# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# TODO The API is returning on both a POST and GET. Make sure to authenticate.

from celery.utils.log import get_task_logger
from django.http import JsonResponse
from rest_framework import viewsets, serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import list_route

from seed.authentication import SEEDAuthentication
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    Organization,
)
from seed.models.data_quality import (
    DATA_TYPES as DATA_QUALITY_DATA_TYPES,
    SEVERITY as DATA_QUALITY_SEVERITY,
    DataQualityCheck,
)
from seed.utils.api import api_endpoint_class
from seed.data_importer.tasks import do_checks

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
    return dict(DATA_QUALITY_DATA_TYPES).get(data_type)


def _get_js_rule_severity(severity):
    """return the JS friendly severity name for the data data_quality rule

    :param severity: data data_quality rule severity as defined in data_quality.models
    :returns: (string) JS severity name
    """
    return dict(DATA_QUALITY_SEVERITY).get(severity)


def _get_rule_type_from_js(data_type):
    """return the Rules TYPE from the JS friendly data type

    :param data_type: 'string', 'number', 'date', or 'year'
    :returns: int data type as defined in data_quality.models
    """
    d = {v: k for k, v in dict(DATA_QUALITY_DATA_TYPES).items()}
    return d.get(data_type)


def _get_severity_from_js(severity):
    """return the Rules SEVERITY from the JS friendly severity

    :param severity: 'error', or 'warning'
    :returns: int severity as defined in data_quality.models
    """
    d = {v: k for k, v in dict(DATA_QUALITY_SEVERITY).items()}
    return d.get(severity)


class DataQualityViews(viewsets.ViewSet):
    """
    Handles Data Quality API operations within Inventory backend.
    (1) Post, wait, get…
    (2) Respond with what changed
    """
    authentication_classes = (SessionAuthentication, SEEDAuthentication)

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

        # step 1: validate the check IDs all exist
        # step 2: validate the check IDs all belong to this organization ID
        # step 3: validate the actual user belongs to the passed in org ID
        # step 4: kick off a background task
        return_value = do_checks(property_state_ids, taxlot_state_ids)
        # step 5: create a new model instance
        return JsonResponse({
            'num_properties': len(property_state_ids),
            'num_taxlots': len(taxlot_state_ids),
            'progress_key': return_value['progress_key']})

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @list_route(methods=['GET'])
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
        org = Organization.objects.get(pk=request.query_params['organization_id'])

        result = {
            'status': 'success',
            'rules': {
                'properties': [],
                'taxlots': []
            }
        }

        dq = DataQualityCheck.retrieve(org)
        rules = dq.rules.order_by('field', 'severity')
        for rule in rules:
            result['rules']['properties' if rule.table_name == 'PropertyState' else 'taxlots'].append({
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
    @list_route(methods=['PUT'])
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
        org = Organization.objects.get(pk=request.query_params['organization_id'])

        dq = DataQualityCheck.retrieve(org)
        dq.reset_all_rules()
        return self.data_quality_rules(request)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @list_route(methods=['PUT'])
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
        org = Organization.objects.get(pk=request.query_params['organization_id'])

        dq = DataQualityCheck.retrieve(org)
        dq.reset_default_rules()
        return self.data_quality_rules(request)

    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @list_route(methods=['POST'])
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
        org = Organization.objects.get(pk=request.query_params['organization_id'])

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

        dq = DataQualityCheck.retrieve(org)
        dq.remove_all_rules()
        for rule in updated_rules:
            try:
                dq.add_rule(rule)
            except TypeError as e:
                return JsonResponse({
                    'status': 'error',
                    'message': e,
                }, status=status.HTTP_400_BAD_REQUEST)

        return self.data_quality_rules(request)
