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
from seed.utils.viewsets import UpdateWithoutPatchModelMixin

_log = logging.getLogger(__name__)

# TODO: Move these serializers into seed/serializers (and maybe actually use them...)
class RulesSerializer(serializers.ModelSerializer):
    data_type = serializers.CharField(source='get_data_type_display', required=False)
    status_label = serializers.PrimaryKeyRelatedField(
        queryset=StatusLabel.objects.all(),
        allow_null=True,
        required=False
    )
    severity = serializers.CharField(source='get_severity_display', required=False)

    class Meta:
        model = Rule
        fields = [
            'condition',
            'data_type',
            'enabled',
            'field',
            'id',
            'max',
            'min',
            'not_null',
            'required',
            'rule_type',
            'severity',
            'status_label',
            'text_match',
            'units',
        ]

    def validate_label(self, label):
        """
        Note: DQ Rules can be shared from parent to child but child orgs can
        have their own labels. So, a Rule shouldn't be associated to Labels
        from child orgs. In other words, Rule and associated Label should be
        from the same org.
        """
        if label is not None and label.super_organization_id != self.instance.data_quality_check.organization_id:
            raise serializers.ValidationError(
                f'Label with ID {label.id} not found in organization, {self.instance.data_quality_check.organization.name}.'
            )
        else:
            return label

    def validate(self, data):
        """
        These are validations that involve values between multiple fields.

        Custom validations for field values in isolation should still be
        contained in 'validate_{field_name}' methods which are only checked when
        that field is in 'data'.
        """
        data_invalid = False
        validation_messages = []

        # Rule with SEVERITY setting of "valid" should have a Label.
        severity_is_valid = self.instance.severity == Rule.SEVERITY_VALID
        severity_unchanged = 'get_severity_display' not in data
        severity_will_be_valid = data.get('get_severity_display') == "valid"

        if (severity_is_valid and severity_unchanged) or severity_will_be_valid:
            # Defaulting to "FOO" enables a value check of either "" or None (even if key doesn't exist)
            label_will_be_removed = data.get('status_label', "FOO") in ["", None]
            label_is_not_associated = self.instance.status_label is None
            label_unchanged = 'status_label' not in data
            if label_will_be_removed or (label_is_not_associated and label_unchanged):
                data_invalid = True
                validation_messages.append(
                    'Label must be assigned when using \'Valid\' Data Severity.'
                )

        # Rule must NOT include or exclude an empty string.
        is_include_or_exclude = self.instance.condition in [Rule.RULE_INCLUDE, Rule.RULE_EXCLUDE]
        condition_unchanged = 'condition' not in data
        will_be_include_or_exclude = data.get('condition') in [Rule.RULE_INCLUDE, Rule.RULE_EXCLUDE]

        if (is_include_or_exclude and condition_unchanged) or will_be_include_or_exclude:
            # Defaulting to "FOO" enables a value check of either "" or None (only if key exists)
            text_match_will_be_empty = data.get('text_match', "FOO") in ["", None]
            text_match_is_empty = getattr(self.instance, 'text_match', "FOO") in ["", None]
            text_match_unchanged = 'text_match' not in data

            if text_match_will_be_empty or (text_match_is_empty and text_match_unchanged):
                data_invalid = True
                validation_messages.append(
                    'Rule must not include or exclude an empty string.'
                )

        if data_invalid:
            raise serializers.ValidationError({
                'general_validation_error': validation_messages
            })
        else:
            return data


class DataQualityRulesSerializer(serializers.Serializer):
    properties = serializers.ListField(child=RulesSerializer())
    taxlots = serializers.ListField(child=RulesSerializer())

class SaveDataQualityRulesPayloadSerializer(serializers.Serializer):
    data_quality_rules = DataQualityRulesSerializer()


class DataQualityRulesResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    rules = DataQualityRulesSerializer()


class DataQualityCheckRuleViewSet(viewsets.GenericViewSet, UpdateWithoutPatchModelMixin):
    serializer_class = RulesSerializer
    model = Rule
    pagination_class = None

    def get_queryset(self):
        org_id = self.kwargs.get('nested_organization_id')
        rule_id = self.kwargs.get('pk')

        if rule_id is None:
            return DataQualityCheck.retrieve(org_id).rules.all()
        else:
            return DataQualityCheck.retrieve(org_id).rules.filter(id=rule_id)

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
