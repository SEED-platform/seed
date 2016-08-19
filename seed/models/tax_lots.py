# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

from django.db import models
from django_pgjson.fields import JsonField
from django.db.models.fields.related import ManyToManyField

from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    StatusLabel,
    Cycle
)


class TaxLot(models.Model):
    # NOTE: we have been calling this the super_organization. We
    # should stay consistent although I prefer the name organization (!super_org)
    organization = models.ForeignKey(Organization)

    def __unicode__(self):
        return u'TaxLot - %s' % (self.pk)


class TaxLotState(models.Model):
    # The state field names should match pretty close to the pdf, just
    # because these are the most 'public' fields in terms of
    # communicating with the cities.

    # import_record = models.ForeignKey(ImportRecord)
    confidence = models.FloatField(default=0, null=True, blank=True)

    jurisdiction_taxlot_identifier = models.CharField(max_length=255,
                                                      null=True, blank=True)
    block_number = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    number_properties = models.IntegerField(null=True, blank=True)

    extra_data = JsonField(default={}, blank=True)

    def __unicode__(self):
        return u'TaxLot State - %s' % (self.pk)


class TaxLotView(models.Model):
    # TODO: Are all foreignkeys automatically indexed?
    taxlot = models.ForeignKey(TaxLot, related_name='views', null=True)
    state = models.ForeignKey(TaxLotState)
    cycle = models.ForeignKey(Cycle)

    labels = ManyToManyField(StatusLabel)

    def __unicode__(self):
        return u'TaxLot View - %s' % (self.pk)

    # FIXME: Add unique constraint on (property, cycle) -- NL: isn't that already below?
    class Meta:
        unique_together = ('taxlot', 'cycle',)
