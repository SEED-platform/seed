# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""
import logging

from django.utils.decorators import method_decorator

from drf_yasg.utils import swagger_auto_schema, no_body

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import (
    ListModelMixin,
    DestroyModelMixin,
    CreateModelMixin,
)

from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.models.data_quality import DataQualityCheck, Rule
from seed.serializers.rules import RuleSerializer
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import UpdateWithoutPatchModelMixin

_log = logging.getLogger(__name__)


nested_org_id_path_field = AutoSchemaHelper.base_field(
    "nested_organization_id",
    "IN_PATH",
    "Organization ID - identifier used to specify a DataQualityCheck and its Rules",
    True,
    "TYPE_INTEGER"
)


@method_decorator(
    name='list',
    decorator=swagger_auto_schema(manual_parameters=[nested_org_id_path_field])
)
@method_decorator(
    name='update',
    decorator=swagger_auto_schema(manual_parameters=[nested_org_id_path_field])
)
@method_decorator(
    name='destroy',
    decorator=swagger_auto_schema(manual_parameters=[nested_org_id_path_field])
)
@method_decorator(
    name='create',
    decorator=swagger_auto_schema(manual_parameters=[nested_org_id_path_field])
)
class DataQualityCheckRuleViewSet(viewsets.GenericViewSet, ListModelMixin, UpdateWithoutPatchModelMixin, DestroyModelMixin, CreateModelMixin):
    serializer_class = RuleSerializer
    model = Rule
    pagination_class = None
    permission_classes = (SEEDOrgPermissions,)

    # allow nested_organization_id to be used for authorization (ie in has_perm_class)
    authz_org_id_kwarg = 'nested_organization_id'

    def get_queryset(self):
        # Handle the anonymous case (e.g. Swagger page load)
        if not self.kwargs:
            return Rule.objects.none()

        org_id = self.kwargs.get('nested_organization_id')
        rule_id = self.kwargs.get('pk')

        if rule_id is None:
            return DataQualityCheck.retrieve(org_id).rules.all()
        else:
            return DataQualityCheck.retrieve(org_id).rules.filter(id=rule_id)

    @swagger_auto_schema(
        manual_parameters=[nested_org_id_path_field],
        request_body=no_body,
        responses={200: RuleSerializer(many=True)}
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_owner')
    @action(detail=False, methods=['PUT'])
    def reset(self, request, nested_organization_id=None):
        """
        Resets an organization's data data_quality rules
        """
        # TODO: Refactor to get all the rules for a DataQualityCheck object directly.
        # At that point, nested_organization_id should be changed to data_quality_check_id
        dq = DataQualityCheck.retrieve(nested_organization_id)
        dq.remove_all_rules()
        return self.list(request, nested_organization_id)
