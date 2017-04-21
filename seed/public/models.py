# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

Because migrations are complicated, we're keeping our public fields here.

This deals with circular dependency issues between LANDINGUser and Organization
"""
from django.db import models
from django_extensions.db.models import TimeStampedModel

from seed.lib.superperms.orgs.models import ExportableField, Organization

INTERNAL = 0
PUBLIC = 1

FIELD_CHOICES = (
    (INTERNAL, 'Internal'),
    (PUBLIC, 'Public')
)


class SharedBuildingField(TimeStampedModel):
    """BuildingSnapshot Exported Field, either public or internally shared."""
    org = models.ForeignKey(Organization)
    field = models.ForeignKey(ExportableField)
    field_type = models.IntegerField(default=INTERNAL, choices=FIELD_CHOICES)

    def __unicode__(self):
        return u'{0} - {1} - {2}'.format(
            self.org, self.field.name, self.get_field_type_display()
        )
