# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

from django.db import models
from django_pgjson.fields import JsonField

from seed.lib.superperms.orgs.models import Organization
from seed.models import Cycle


class Property(models.Model):
    organization = models.ForeignKey(Organization)
    campus = models.BooleanField(default=False)
    parent_property = models.ForeignKey('Property', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'properties'

    def __unicode__(self):
        return u'Property - %s' % (self.pk)


class PropertyState(models.Model):
    # import_record = models.ForeignKey(ImportRecord)
    confidence = models.FloatField(default=0, null=True, blank=True)

    jurisdiction_property_identifier = models.CharField(max_length=255,
                                                        null=True, blank=True)
    pm_parent_property_id = models.CharField(max_length=255, null=True,
                                             blank=True)
    lot_number = models.CharField(max_length=255, null=True, blank=True)
    property_name = models.CharField(max_length=255, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    building_count = models.IntegerField(null=True,
                                         blank=True)  # Only spot where it's 'building' in the app, b/c this is a PortMgr field.
    property_notes = models.TextField(null=True, blank=True)
    year_ending = models.DateField(null=True, blank=True)
    use_description = models.CharField(max_length=255, null=True,
                                       blank=True)  # Tax IDs are often stuck in here.
    gross_floor_area = models.FloatField(null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)
    recent_sale_date = models.DateTimeField(null=True, blank=True)
    conditioned_floor_area = models.FloatField(null=True, blank=True)
    occupied_floor_area = models.FloatField(null=True, blank=True)
    owner = models.CharField(max_length=255, null=True, blank=True)
    owner_email = models.CharField(max_length=255, null=True, blank=True)
    owner_telephone = models.CharField(max_length=255, null=True, blank=True)
    owner_address = models.CharField(max_length=255, null=True, blank=True)
    owner_city_state = models.CharField(max_length=255, null=True, blank=True)
    owner_postal_code = models.CharField(max_length=255, null=True, blank=True)
    building_portfolio_manager_identifier = models.CharField(max_length=255,
                                                             null=True,
                                                             blank=True)
    building_home_energy_score_identifier = models.CharField(max_length=255,
                                                             null=True,
                                                             blank=True)
    energy_score = models.IntegerField(null=True, blank=True)
    site_eui = models.FloatField(null=True, blank=True)
    generation_date = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)
    source_eui_weather_normalized = models.FloatField(null=True, blank=True)
    site_eui_weather_normalized = models.FloatField(null=True, blank=True)
    source_eui = models.FloatField(null=True, blank=True)
    energy_alerts = models.TextField(null=True, blank=True)
    space_alerts = models.TextField(null=True, blank=True)
    building_certification = models.CharField(max_length=255, null=True,
                                              blank=True)

    extra_data = JsonField(default={}, blank=True)

    def __unicode__(self):
        return u'Property State - %s' % (self.pk)


class PropertyView(models.Model):
    property = models.ForeignKey(Property, related_name='views')
    cycle = models.ForeignKey(Cycle)
    state = models.ForeignKey(PropertyState)

    def __unicode__(self):
        return u'Property View - %s' % (self.pk)

    # FIXME: Add unique constraint on (property, cycle)
    class Meta:
        unique_together = ('property', 'cycle',)
