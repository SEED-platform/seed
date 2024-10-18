"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from seed.models import Service
from seed.serializers.systems import ServiceSerializer
from seed.utils.api import OrgMixin
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger()


class ServiceViewSet(ModelViewSetWithoutPatch, OrgMixin):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        group_pk = self.kwargs.get("inventory_group_pk")
        system_pk = self.kwargs.get("system_pk")
        return Service.objects.filter(
            system=system_pk, system__group=group_pk, system__group__organization=self.get_organization(self.request)
        )
