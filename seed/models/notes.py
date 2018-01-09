# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from seed.models import (
    Property,
    TaxLot,
)
# from seed.lib.superperms.orgs.models import Organization
from seed.models.projects import Project
from seed.utils.generic import obj_to_dict


class Note(models.Model):
    name = models.CharField(_('name'), max_length=Project.PROJECT_NAME_MAX_LENGTH)
    text = models.TextField()

    # organization = models.ForeignKey(Organization, blank=True, null=True, related_name='notes')
    property = models.ForeignKey(Property, null=True, related_name='notes')
    taxlot = models.ForeignKey(TaxLot, null=True, related_name='notes')

    # Track when the entry was created and when it was updated
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    DEFAULT_LABELS = [
        "Residential",
        "Non-Residential",
        "Violation",
        "Compliant",
        "Missing Data",
        "Questionable Report",
        "Update Bldg Info",
        "Call",
        "Email",
        "High EUI",
        "Low EUI",
        "Exempted",
        "Extension",
        "Change of Ownership",
    ]

    class Meta:
        ordering = ['-created']

    def to_dict(self):
        return obj_to_dict(self)
