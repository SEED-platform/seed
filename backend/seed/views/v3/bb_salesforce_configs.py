"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_serializer, extend_schema_view
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import BBSalesforceConfig
from seed.serializers.bb_salesforce_config import BBSalesforceConfigSerializer
from seed.utils.api import OrgQuerySetMixin
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger(__name__)


# The organization is always taken from the query string
bb_salesforce_config_body = AutoSchemaHelper.json_body({"salesforce_url": "string", "client_id": "string", "client_secret": "string"})


@extend_schema_serializer(many=False)
class BBSalesforceConfigResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    bb_salesforce_configs = BBSalesforceConfigSerializer()


@extend_schema_org_query_param
@extend_schema_view(
    create=extend_schema(request=bb_salesforce_config_body),
    update=extend_schema(request=bb_salesforce_config_body),
)
@method_decorator(has_perm("requires_owner"), name="retrieve")
@method_decorator(has_perm("requires_owner"), name="create")
@method_decorator(has_perm("requires_owner"), name="update")
@method_decorator(has_perm("requires_owner"), name="destroy")
class BBSalesforceConfigsViewSet(OrgQuerySetMixin, ModelViewSetWithoutPatch):
    model = BBSalesforceConfig
    serializer_class = BBSalesforceConfigSerializer
    queryset = BBSalesforceConfig.objects.all()
    # `list` returns the organization's single config
    pagination_class = None

    def get_serializer(self, *args, **kwargs):
        # A config can only be written to the organization in the query string
        if "data" in kwargs:
            kwargs["data"] = kwargs["data"].copy()
            kwargs["data"]["organization"] = self.get_organization(self.request)
        return super().get_serializer(*args, **kwargs)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not settings.SEED_SALESFORCE_ENABLED:
            raise PermissionDenied("Salesforce is disabled on this deployment")

    @extend_schema(
        responses={
            200: OpenApiResponse(
                BBSalesforceConfigResponseSerializer,
                description="`bb_salesforce_configs` is an empty object if the organization has no BB Salesforce config",
            )
        }
    )
    @method_decorator(
        [
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

    @extend_schema(request=bb_salesforce_config_body, responses={200: BBSalesforceConfigResponseSerializer})
    @method_decorator(
        [
            ajax_request,
            has_perm("requires_owner"),
        ],
    )
    @action(detail=False, methods=["PUT"])
    def update_config(self, request):
        """Create or update the organization's BB Salesforce config"""
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
