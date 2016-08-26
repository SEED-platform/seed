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
from django.db.models.fields.related import ManyToManyField
from seed.models import Cycle
from seed.models import StatusLabel
from auditlog import AUDIT_IMPORT
from auditlog import DATA_UPDATE_TYPE

# Oops! we override a builtin in some of the models
property_decorator = property


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

    # Only spot where it's 'building' in the app, b/c this is a PortMgr field.
    building_count = models.IntegerField(null=True, blank=True)

    property_notes = models.TextField(null=True, blank=True)
    year_ending = models.DateField(null=True, blank=True)

    # Tax IDs are often stuck here.
    use_description = models.CharField(max_length=255, null=True, blank=True)

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

    labels = ManyToManyField(StatusLabel)

    def __unicode__(self):
        return u'Property View - %s' % (self.pk)

    class Meta:
        unique_together = ('property', 'cycle',)

    def __init__(self, *args, **kwargs):
        self._import_filename = kwargs.pop('import_filename', None)
        super(PropertyView, self).__init__(*args, **kwargs)

    def initialize_audit_logs(self, **kwargs):
        kwargs.update({
            'organization': self.property.organization,
            'state': self.state,
            'view': self,
            'record_type': AUDIT_IMPORT
        })
        return PropertyAuditLog.objects.create(**kwargs)

    def update_state(self, new_state, **kwds):
        view_audit_log = PropertyAuditLog.objects.filter(
            state=self.state
        ).first()
        if not view_audit_log:
            view_audit_log = self.initialize_audit_logs(
                description="Initial audit log added on update.",
                record_type=AUDIT_IMPORT,
            )
        new_audit_log = PropertyAuditLog(
            organization=self.property.organization,
            parent1=view_audit_log,
            state=new_state,
            view=self,
            **kwds
        )
        self.state = new_state
        self.save()
        new_audit_log.save()
        return

    def save(self, *args, **kwargs):
        # create audit log on creation
        audit_log_initialized = True if self.id else False
        import_filename = kwargs.pop('import_filename', self._import_filename)
        super(PropertyView, self).save(*args, **kwargs)
        if not audit_log_initialized:
            self.initialize_audit_logs(
                description="Initial audit log added on creation/save.",
                record_type=AUDIT_IMPORT,
                import_filename=import_filename
            )

    @property_decorator
    def import_filename(self):
        """Get the import file name form the audit logs"""
        if not getattr(self, '_import_filename', None):
            audit_log = PropertyAuditLog.objects.filter(
                view_id=self.pk).order_by('created').first()
            self._import_filename = audit_log.import_filename
        return self._import_filename


class PropertyAuditLog(models.Model):
    organization = models.ForeignKey(Organization)
    parent1 = models.ForeignKey('PropertyAuditLog', blank=True, null=True, related_name='propertyauditlog__parent1')
    parent2 = models.ForeignKey('PropertyAuditLog', blank=True, null=True, related_name='propertyauditlog__parent2')

    state = models.ForeignKey('PropertyState', related_name='propertyauditlog__state')
    view = models.ForeignKey('PropertyView', related_name='propertyauditlog__view', null=True)

    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    import_filename = models.CharField(max_length=255, null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)
