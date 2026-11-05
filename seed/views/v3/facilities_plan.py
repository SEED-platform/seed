"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

import logging

from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import ValidationError

from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import FacilitiesPlan
from seed.serializers.facilities_plan import FacilitiesPlanSerializer
from seed.utils.api_schema import AutoSchemaHelper, extend_schema_org_query_param
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

logger = logging.getLogger(__name__)

# Writes are authorized against `organization_id`, or the body's `organization` when it is omitted
optional_org_id_field = AutoSchemaHelper.query_org_id_field(
    required=False, description="Organization ID (defaults to the body's `organization`, then to your default organization)"
)


@extend_schema_view(
    list=extend_schema_org_query_param,
    retrieve=extend_schema_org_query_param,
    create=extend_schema(parameters=[optional_org_id_field]),
    update=extend_schema(parameters=[optional_org_id_field]),
    destroy=extend_schema(parameters=[optional_org_id_field]),
)
@method_decorator(
    [
        has_perm("requires_viewer"),
    ],
    name="retrieve",
)
@method_decorator(
    [
        has_perm("requires_viewer"),
    ],
    name="list",
)
class FacilitiesPlanViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """An organization's facilities plans: the columns and energy threshold used to rank properties"""

    serializer_class = FacilitiesPlanSerializer
    model = FacilitiesPlan
    pagination_class = None

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        return FacilitiesPlan.objects.filter(organization_id=org_id)

    def perform_create(self, serializer):
        self._validate_organization(serializer.validated_data)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self._validate_organization(serializer.validated_data)
        super().perform_update(serializer)

    def _validate_organization(self, validated_data):
        """Reject an organization, or columns, other than the requested organization"""
        org_id = int(self.get_organization(self.request))
        errors = {
            field: ["Must belong to the requested organization."]
            for field, value in validated_data.items()
            if (field == "organization" and value.id != org_id)
            or (field.endswith("_column") and value is not None and value.organization_id != org_id)
        }
        if errors:
            raise ValidationError(errors)
