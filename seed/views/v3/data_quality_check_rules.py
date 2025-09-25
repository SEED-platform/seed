"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.utils.decorators import method_decorator
from drf_yasg.utils import no_body, swagger_auto_schema
from rest_framework.decorators import action

from seed.decorators import ajax_request
from seed.lib.superperms.orgs.decorators import has_perm
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.models.data_quality import DataQualityCheck, Rule
from seed.serializers.rules import RuleSerializer
from seed.utils.api import api_endpoint
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import ModelViewSetWithoutPatch

_log = logging.getLogger(__name__)


nested_org_id_path_field = AutoSchemaHelper.base_field(
    "nested_organization_id",
    "IN_PATH",
    "Organization ID - identifier used to specify a DataQualityCheck and its Rules",
    True,
    "TYPE_INTEGER",
)


@method_decorator([swagger_auto_schema(manual_parameters=[nested_org_id_path_field])], name="list")
@method_decorator([swagger_auto_schema(manual_parameters=[nested_org_id_path_field])], name="retrieve")
@method_decorator([swagger_auto_schema(manual_parameters=[nested_org_id_path_field])], name="update")
@method_decorator([swagger_auto_schema(manual_parameters=[nested_org_id_path_field])], name="destroy")
@method_decorator([swagger_auto_schema(manual_parameters=[nested_org_id_path_field])], name="create")
class DataQualityCheckRuleViewSet(ModelViewSetWithoutPatch):
    serializer_class = RuleSerializer
    model = Rule
    pagination_class = None
    permission_classes = (SEEDOrgPermissions,)

    # allow nested_organization_id to be used for authorization (i.e., in has_perm)
    authz_org_id_kwarg = "nested_organization_id"

    def get_queryset(self):
        # Handle the anonymous case (e.g., Swagger page load)
        if not self.kwargs:
            return Rule.objects.none()

        org_id = self.kwargs.get("nested_organization_id")
        rule_id = self.kwargs.get("pk")

        if rule_id is None:
            return DataQualityCheck.retrieve(org_id).rules.all()
        else:
            return DataQualityCheck.retrieve(org_id).rules.filter(id=rule_id)

    @swagger_auto_schema(manual_parameters=[nested_org_id_path_field], request_body=no_body, responses={200: RuleSerializer(many=True)})
    @method_decorator(
        [
            api_endpoint,
            ajax_request,
            has_perm("requires_owner"),
        ]
    )
    @action(detail=False, methods=["PUT"])
    def reset(self, request, nested_organization_id=None):
        """
        Resets an organization's data_quality rules
        """
        # TODO: Refactor to get all the rules for a DataQualityCheck object directly.
        # At that point, nested_organization_id should be changed to data_quality_check_id
        dq = DataQualityCheck.retrieve(nested_organization_id)
        dq.remove_all_rules()
        return self.list(request, nested_organization_id)
