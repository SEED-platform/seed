"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author 'Piper Merriam <pmerriam@quickleft.com>'
"""

import logging

from django.utils.decorators import method_decorator

from seed.lib.superperms.orgs.decorators import has_hierarchy_access, has_perm_class
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.models import FacilitiesPlanRun
from seed.serializers.facilities_plan_run import FacilitiesPlanRunSerializer
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet

logger = logging.getLogger(__name__)


@method_decorator(
    name="retrieve",
    decorator=[
        has_perm_class("requires_viewer"),
        has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
    ],
)
@method_decorator(
    name="list",
    decorator=[
        has_perm_class("requires_viewer"),
        # has_hierarchy_access(facilities_plan_run_id_kwarg="pk"),
    ],
)
class FacilitiesPlanRunViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    serializer_class = FacilitiesPlanRunSerializer
    model = FacilitiesPlanRun
    pagination_class = None

    def get_queryset(self):
        org_id = self.get_organization(self.request)
        fprs = FacilitiesPlanRun.objects.filter(ali__organization=org_id)

        access_level_instance_id = getattr(self.request, "access_level_instance_id", None)
        if access_level_instance_id:
            access_level_instance = AccessLevelInstance.objects.get(pk=access_level_instance_id)
            fprs = fprs.filter(ali__lft__gte=access_level_instance.lft, ali__rgt__lte=access_level_instance.rgt)

        return fprs
