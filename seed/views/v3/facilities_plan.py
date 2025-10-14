"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

import logging

from django.utils.decorators import method_decorator

from seed.lib.superperms.orgs.decorators import has_perm
from seed.models import FacilitiesPlan
from seed.serializers.facilities_plan import FacilitiesPlanSerializer
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

logger = logging.getLogger(__name__)


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
    serializer_class = FacilitiesPlanSerializer
    model = FacilitiesPlan
    pagination_class = None

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        return FacilitiesPlan.objects.filter(organization_id=org_id)
