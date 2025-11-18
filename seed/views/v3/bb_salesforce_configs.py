"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import BBSalesforceConfig
from seed.serializers.bb_salesforce_config import BBSalesforceConfigSerializer
from seed.serializers.systems import ServiceSerializer
from seed.utils.api import OrgMixin
from seed.utils.api_schema import swagger_auto_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger()


class BBSalesforceConfigsViewSet(ModelViewSetWithoutPatch, OrgMixin):
    model = BBSalesforceConfig
    serializer_class = ServiceSerializer
    queryset = BBSalesforceConfig.objects.all()

    @method_decorator(
        [
            swagger_auto_schema_org_query_param,
            ajax_request,
            has_perm("requires_owner"),
        ],
    )
    def list(self, request):
        organization_id = self.get_organization(request)
        bb_salesforce_configs = BBSalesforceConfig.objects.filter(organization_id=organization_id).first()

        if bb_salesforce_configs is not None:
            bb_salesforce_configs_data = BBSalesforceConfigSerializer(bb_salesforce_configs).data
        else:
            bb_salesforce_configs_data = {}  # or None, depending on your frontend expectations

        return JsonResponse(
            {
                "status": "success",
                "bb_salesforce_configs": bb_salesforce_configs_data,
            },
            status=status.HTTP_200_OK,
        )

    @method_decorator(
        [
            swagger_auto_schema_org_query_param,
            ajax_request,
            has_perm("requires_owner"),
        ],
    )
    @action(detail=False, methods=["PUT"])
    def update_config(self, request):
        organization_id = self.get_organization(request)
        bb_salesforce_configs = BBSalesforceConfig.objects.filter(organization_id=organization_id).first()
        bb_salesforce_configs = BBSalesforceConfigSerializer(bb_salesforce_configs, data={**request.data, "organization": organization_id})

        if not bb_salesforce_configs.is_valid():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Bad request",
                    "errors": bb_salesforce_configs.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        bb_salesforce_configs.save()

        return JsonResponse(
            {
                "status": "success",
                "bb_salesforce_configs": bb_salesforce_configs.data,
            },
            status=status.HTTP_200_OK,
        )
