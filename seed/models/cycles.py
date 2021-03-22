# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
"""

from __future__ import unicode_literals

from datetime import date, datetime

from django.db import models
from django.utils import timezone

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization


class Cycle(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='cycles', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=255)
    start = models.DateTimeField()
    end = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return 'Cycle - %s' % self.name

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

    @classmethod
    def get_or_create_default(cls, organization):
        year = date.today().year - 1
        cycle_name = '{} Calendar Year'.format(year)
        cycle = Cycle.objects.filter(name=cycle_name, organization=organization).first()
        if not cycle:
            return Cycle.objects.create(
                name=cycle_name,
                organization=organization,
                start=datetime(year, 1, 1, tzinfo=timezone.get_current_timezone()),
                end=datetime(year + 1, 1, 1, tzinfo=timezone.get_current_timezone())
            )
        else:
            return cycle
