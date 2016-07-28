# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import unicodedata

from django.db import models
from django_pgjson.fields import JsonField

from seed.utils.generic import split_model_fields
from seed.lib.superperms.orgs.models import Organization
from seed.models import (Cycle, ImportFile, obj_to_dict)


class Property(models.Model):
    """The canonical property"""
    organization = models.ForeignKey(Organization)

    # Handle properties that may have multiple properties (e.g. buildings)
    campus = models.BooleanField(default=False)
    parent_property = models.ForeignKey('Property', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'properties'

    def __unicode__(self):
        return u'Property - %s' % (self.pk)


class PropertyState(models.Model):
    """Store a single property"""
    # import_record = models.ForeignKey(ImportRecord)
    # Support finding the property by the import_file and source_type
    import_file = models.ForeignKey(ImportFile, null=True, blank=True)
    # FIXME: source_type needs to be a foreign key or make it import_file.source_type
    source_type = models.IntegerField(null=True, blank=True, db_index=True)
    super_organization = models.ForeignKey(Organization, blank=True, null=True)

    confidence = models.FloatField(default=0, null=True, blank=True)

    # TODO: hmm, name this jurisdiction_property_id to stay consistent?
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

    def clean(self, *args, **kwargs):
        date_field_names = (
            'year_ending',
            'generation_date',
            'release_date',
            'recent_sale_date'
        )

        # TODO: Where to put in the custom_id_1
        # custom_id_1 = getattr(self, 'custom_id_1')
        # if isinstance(custom_id_1, unicode):
        #     custom_id_1 = unicodedata.normalize('NFKD', custom_id_1).encode(
        #         'ascii', 'ignore'
        #     )
        # if custom_id_1 and len(str(custom_id_1)) > 128:
        #     self.custom_id_1 = custom_id_1[:128]
        for field in date_field_names:
            value = getattr(self, field)
            if value and isinstance(value, basestring):
                setattr(self, field, convert_datestr(value))

    def to_dict(self, fields=None, include_related_data=True):
        """
        Returns a dict version of the PropertyState, either with all fields
        or masked to just those requested.
        """
        if fields:
            model_fields, ed_fields = split_model_fields(self, fields)
            extra_data = self.extra_data
            ed_fields = filter(lambda f: f in extra_data, ed_fields)

            result = {
                field: getattr(self, field) for field in model_fields
                }
            result['extra_data'] = {
                field: extra_data[field] for field in ed_fields
                }

            # always return id's and canonical_building id's
            result['id'] = result['pk'] = self.pk

            # TODO: I don't think this is needed anymore
            result['canonical_building'] = (
                self.canonical_building and self.canonical_building.pk
            )

            # should probably also return children, parents, and coparent
            # result['children'] = map(lambda c: c.id, self.children.all())
            # result['parents'] = map(lambda p: p.id, self.parents.all())
            # result['co_parent'] = (self.co_parent and self.co_parent.pk)
            # result['coparent'] = (self.co_parent and {
            #     field: self.co_parent.pk for field in ['pk', 'id']
            #     })

            return result

        d = obj_to_dict(self, include_m2m=include_related_data)

        # if include_related_data:
            # d['parents'] = list(self.parents.values_list('id', flat=True))
            # d['co_parent'] = self.co_parent.pk if self.co_parent else None

        return d


class PropertyView(models.Model):
    """Similar to the old world of canonical building"""
    property = models.ForeignKey(Property, related_name='views') # different property views can be associated with each other (2012, 2013).
    cycle = models.ForeignKey(Cycle)
    state = models.ForeignKey(PropertyState)

    def __unicode__(self):
        return u'Property View - %s' % (self.pk)

    # FIXME: Add unique constraint on (property, cycle)
    class Meta:
        unique_together = ('property', 'cycle',)
