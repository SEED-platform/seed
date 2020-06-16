# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""
import logging

from django.db import transaction
from django.http import JsonResponse

from drf_yasg.utils import swagger_auto_schema

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.data_quality import DataQualityCheck, Rule
from seed.models import StatusLabel
from seed.serializers.notes import (
    NoteSerializer,
)
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgCreateUpdateModelViewSet

_log = logging.getLogger(__name__)

# TODO: Move these serializers into seed/serializers (and maybe actually use them...)
class RulesSerializer(serializers.ModelSerializer):
    data_type = serializers.CharField(source='get_data_type_display')
    label = serializers.SlugRelatedField(source="status_label", queryset=StatusLabel.objects.all(), slug_field='id')
    severity = serializers.CharField(source='get_severity_display')

    class Meta:
        model = Rule
        fields = [
            'condition',
            'data_type',
            'enabled',
            'field',
            'label',
            'max',
            'min',
            'not_null',
            'required',
            'rule_type',
            'severity',
            'text_match',
            'units',
        ]


class DataQualityRulesSerializer(serializers.Serializer):
    properties = serializers.ListField(child=RulesSerializer())
    taxlots = serializers.ListField(child=RulesSerializer())

class SaveDataQualityRulesPayloadSerializer(serializers.Serializer):
    data_quality_rules = DataQualityRulesSerializer()


class DataQualityRulesResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    rules = DataQualityRulesSerializer()


# TODO: convert these to serializers
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


class RuleViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                "nested_organization_id",
                "IN_PATH",
                "Organization ID - identifier used to specify a DataQualityCheck and its Rules",
                True,
                "TYPE_INTEGER"
            )
        ],
        responses={
            200: DataQualityRulesResponseSerializer
        }
    )
    @has_perm_class('requires_member')
    @api_endpoint_class
    @ajax_request_class
    def list(self, request, nested_organization_id=None):
        """
        Returns the data quality rules for an org.
        """

        result = {
            'status': 'success',
            'rules': {
                'properties': [],
                'taxlots': []
            }
        }

        # TODO: Refactor to get all the rules for a DataQualityCheck object directly.
        # At that point, nested_organization_id should be changed to data_quality_check_id
        dq = DataQualityCheck.retrieve(nested_organization_id)

        property_rules = dq.rules.filter(table_name='PropertyState').order_by('field', 'severity')
        taxlot_rules = dq.rules.filter(table_name='TaxLotState').order_by('field', 'severity')

        result['rules']['properties'] = RulesSerializer(property_rules, many=True).data
        result['rules']['taxlots'] = RulesSerializer(taxlot_rules, many=True).data

        return JsonResponse(result)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                "nested_organization_id",
                "IN_PATH",
                "Organization ID - identifier used to specify a DataQualityCheck and its Rules",
                True,
                "TYPE_INTEGER"
            )
        ],
        responses={
            200: DataQualityRulesResponseSerializer
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['PUT'])
    def reset(self, request, nested_organization_id=None):
        """
        Resets an organization's data data_quality rules
        """
        # TODO: Refactor to get all the rules for a DataQualityCheck object directly.
        # At that point, nested_organization_id should be changed to data_quality_check_id
        dq = DataQualityCheck.retrieve(nested_organization_id)
        dq.reset_default_rules()
        return self.list(request, nested_organization_id)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                "nested_organization_id",
                "IN_PATH",
                "Organization ID - identifier used to specify a DataQualityCheck and its Rules",
                True,
                "TYPE_INTEGER"
            )
        ],
        request_body=SaveDataQualityRulesPayloadSerializer,
        responses={
            200: DataQualityRulesResponseSerializer
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['POST'])
    def batch_save(self, request, nested_organization_id=None):
        """
        Saves an organization's settings: name, query threshold, shared fields.
        The method passes in all the fields again, so it is okay to remove
        all the rules in the db, and just recreate them (albeit inefficient)
        """
        body = request.data
        if body.get('data_quality_rules') is None:
            return JsonResponse({
                'status': 'error',
                'message': 'missing the data_quality_rules'
            }, status=status.HTTP_404_NOT_FOUND)

        posted_rules = body['data_quality_rules']
        updated_rules = []
        valid_rules = True
        validation_messages = set()
        for rule in posted_rules['properties']:
            if _get_severity_from_js(rule['severity']) == Rule.SEVERITY_VALID and rule['label'] is None:
                valid_rules = False
                validation_messages.add('Label must be assigned when using Valid Data Severity.')
            if rule['condition'] == Rule.RULE_INCLUDE or rule['condition'] == Rule.RULE_EXCLUDE:
                if rule['text_match'] is None or rule['text_match'] == '':
                    valid_rules = False
                    validation_messages.add('Rule must not include or exclude an empty string.')
            updated_rules.append(
                {
                    'field': rule['field'],
                    'table_name': 'PropertyState',
                    'enabled': rule['enabled'],
                    'condition': rule['condition'],
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
            if _get_severity_from_js(rule['severity']) == Rule.SEVERITY_VALID and rule['label'] is None:
                valid_rules = False
                validation_messages.add('Label must be assigned when using Valid Data Severity.')
            if rule['condition'] == Rule.RULE_INCLUDE or rule['condition'] == Rule.RULE_EXCLUDE:
                if rule['text_match'] is None or rule['text_match'] == '':
                    valid_rules = False
                    validation_messages.add('Rule must not include or exclude an empty string.')
            updated_rules.append(
                {
                    'field': rule['field'],
                    'table_name': 'TaxLotState',
                    'enabled': rule['enabled'],
                    'condition': rule['condition'],
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

        if valid_rules is False:
            return JsonResponse({
                'status': 'error',
                'message': '\n'.join(validation_messages),
            }, status=status.HTTP_400_BAD_REQUEST)

        # This pattern of deleting and recreating Rules is slated to be deprecated
        bad_rule_creation = False
        error_messages = set()
        # TODO: Refactor to get all the rules for a DataQualityCheck object directly.
        # At that point, nested_organization_id should be changed to data_quality_check_id
        dq = DataQualityCheck.retrieve(nested_organization_id)
        dq.remove_all_rules()
        for rule in updated_rules:
            with transaction.atomic():
                try:
                    dq.add_rule(rule)
                except Exception as e:
                    error_messages.add('Rule could not be recreated: ' + str(e))
                    bad_rule_creation = True
                    continue

        if bad_rule_creation:
            return JsonResponse({
                'status': 'error',
                'message': '\n'.join(error_messages),
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return self.list(request, nested_organization_id)
