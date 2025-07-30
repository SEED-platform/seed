"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from seed.models import BBSalesforceConfig
from seed.serializers.systems import ServiceSerializer
from seed.utils.api import OrgMixin
from seed.utils.viewsets import ModelViewSetWithoutPatch

logger = logging.getLogger()


class BBSalesforceConfigsViewSet(ModelViewSetWithoutPatch, OrgMixin):
    model = BBSalesforceConfig
    serializer_class = ServiceSerializer
