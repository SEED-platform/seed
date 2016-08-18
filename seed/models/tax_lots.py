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
from seed.models import StatusLabel
from seed.models import Cycle
from seed.models import PropertyView


class TaxLot(models.Model):
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
    taxlot = models.ForeignKey(TaxLot, related_name='views', null=True)
    state = models.ForeignKey(TaxLotState)
    cycle = models.ForeignKey(Cycle)

    labels = ManyToManyField(StatusLabel)

    def __unicode__(self):
        return u'TaxLot View - %s' % (self.pk)

    # FIXME: Add unique constraint on (property, cycle)
    class Meta:
        unique_together = ('taxlot', 'cycle',)


class TaxLotProperty(models.Model):
    property_view = models.ForeignKey(PropertyView)
    taxlot_view = models.ForeignKey(TaxLotView)

    cycle = models.ForeignKey(Cycle)

    # If there is a complex TaxLot/Property association, this field
    # lists the "main" tax lot that Properties should be reported under.
    # User controlled flag.
    primary = models.BooleanField(default=True)

    def __unicode__(self):
        return u'M2M Property View %s / TaxLot View %s' % (
            self.property_view_id, self.taxlot_view_id)

    class Meta:
        unique_together = ('property_view', 'taxlot_view',)
