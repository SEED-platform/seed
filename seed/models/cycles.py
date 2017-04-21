"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""

from __future__ import unicode_literals

from django.db import models

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization


class Cycle(models.Model):
    organization = models.ForeignKey(Organization, blank=True, null=True)
    user = models.ForeignKey(User, blank=True, null=True)
    name = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return u'Cycle - %s' % self.name

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
