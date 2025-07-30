"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.db import models

from seed.lib.superperms.orgs.models import Organization

logger = logging.getLogger(__name__)


class BBSalesforceConfig(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    salesforce_url = models.CharField(blank=True, max_length=128, null=True)
    client_id = models.CharField(blank=True, max_length=128, null=True)
    client_secret = models.CharField(blank=True, max_length=128, null=True)
