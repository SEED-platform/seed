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
    # queryset = Service.objects.all()

    def get_queryset(self):
        # this needs to consider ALI - list will return all regardless of ali
        return Service.objects.filter(system__group__organization=self.get_organization(self.request))
