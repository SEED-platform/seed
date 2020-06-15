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


class RuleViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                "nested_1_pk",
                "IN_PATH",
                "Organization ID - identifier used to get an organization's Rules",
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
    def list(self, request, nested_1_pk=None):
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
        # At that point, nested_1_pk should be changed to data_quality_check_id
        dq = DataQualityCheck.retrieve(nested_1_pk)

        property_rules = dq.rules.filter(table_name='PropertyState').order_by('field', 'severity')
        taxlot_rules = dq.rules.filter(table_name='TaxLotState').order_by('field', 'severity')

        result['rules']['properties'] = RulesSerializer(property_rules, many=True).data
        result['rules']['taxlots'] = RulesSerializer(taxlot_rules, many=True).data

        return JsonResponse(result)
