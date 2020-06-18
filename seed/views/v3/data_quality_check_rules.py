# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""
import logging

from django.db import transaction
from django.http import JsonResponse

from drf_yasg.utils import swagger_auto_schema

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.renderers import JSONRenderer

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import Organization
from seed.models.data_quality import DataQualityCheck, Rule
from seed.models import StatusLabel
from seed.serializers.rules import (
    DataQualityRulesResponseSerializer,
    RuleSerializer,
)
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import UpdateWithoutPatchModelMixin

_log = logging.getLogger(__name__)


class DataQualityCheckRuleViewSet(viewsets.GenericViewSet, UpdateWithoutPatchModelMixin):
    serializer_class = RuleSerializer
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

        result['rules']['properties'] = RuleSerializer(property_rules, many=True).data
        result['rules']['taxlots'] = RuleSerializer(taxlot_rules, many=True).data

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
