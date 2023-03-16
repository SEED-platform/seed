# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column

logger = logging.getLogger(__name__)


class SalesforceMapping(models.Model):
    """Stores org-defined salesforce to seed field mappings.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name=_('SeedOrg'),
                                     null=False, related_name='salesforce_mappings')

    column = models.ForeignKey(Column, related_name="salesforce_column", null=False, on_delete=models.CASCADE)
    salesforce_fieldname = models.CharField(max_length=255, null=False)

    def __str__(self):
        return 'Mapping - %s' % self.salesforce_fieldname

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['column', 'salesforce_fieldname'], name='unique_column_salesforce_field')
        ]
