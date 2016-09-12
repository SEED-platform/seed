# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

from django.db import models
from django.db.models.fields.related import ManyToManyField
from django_pgjson.fields import JsonField

from auditlog import AUDIT_IMPORT
from auditlog import DATA_UPDATE_TYPE
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Cycle,
    StatusLabel,
)


class TaxLot(models.Model):
    # NOTE: we have been calling this the organization. We
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

    jurisdiction_tax_lot_id = models.CharField(max_length=255, null=True, blank=True)
    block_number = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=255, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    number_properties = models.IntegerField(null=True, blank=True)

    extra_data = JsonField(default={}, blank=True)

    def __unicode__(self):
        return u'TaxLot State - %s' % (self.pk)

    def promote(self, cycle):
        """

        Args:
            cycle:

        Returns:

        """
        return None

        # tls, _ = TaxLotState.objects.get_or_create(
        #     jurisdiction_tax_lot_id=tax_lot_id
        # )
        #
        # logger.debug("the cycle is {}".format(cycle))
        # logger.debug("the taxlotstate is {}".format(tls))
        # tlv, _ = TaxLotView.objects.get_or_create(
        #     state=tls,
        #     cycle=cycle,
        # ).first()
        #
        # logger.debug("taxlotview is {}".format(tlv))


class TaxLotView(models.Model):
    # TODO: Are all foreignkeys automatically indexed?
    taxlot = models.ForeignKey(TaxLot, related_name='views', null=True)
    state = models.ForeignKey(TaxLotState)
    cycle = models.ForeignKey(Cycle)

    labels = ManyToManyField(StatusLabel)

    def __unicode__(self):
        return u'TaxLot View - %s' % (self.pk)

    # TODO: Add unique constraint on (property, cycle) -- NL: isn't that already below?
    class Meta:
        unique_together = ('taxlot', 'cycle',)

    def __init__(self, *args, **kwargs):
        self._import_filename = kwargs.pop('import_filename', None)
        super(TaxLotView, self).__init__(*args, **kwargs)

    def initialize_audit_logs(self, **kwargs):
        kwargs.update({
            'organization': self.taxlot.organization,
            'state': self.state,
            'view': self,
            'record_type': AUDIT_IMPORT
        })
        return TaxLotAuditLog.objects.create(**kwargs)

    def update_state(self, new_state, **kwargs):
        view_audit_log = TaxLotAuditLog.objects.filter(
            state=self.state).first()
        if not view_audit_log:
            view_audit_log = self.initialize_audit_logs(
                description="Initial audit log added on update.",
                record_type=AUDIT_IMPORT,
            )
        new_audit_log = TaxLotAuditLog(
            organization=self.taxlot.organization,
            parent1=view_audit_log,
            state=new_state,
            view=self,
            **kwargs
        )
        self.state = new_state
        self.save()
        new_audit_log.save()
        return

    def save(self, *args, **kwargs):
        # create audit log on creation
        audit_log_initialized = True if self.id else False
        import_filename = kwargs.pop('import_filename', self._import_filename)
        super(TaxLotView, self).save(*args, **kwargs)
        if not audit_log_initialized:
            self.initialize_audit_logs(
                description="Initial audit log added on creation/save.",
                record_type=AUDIT_IMPORT,
                import_filename=import_filename
            )

    @property
    def import_filename(self):
        """Get the import file name form the audit logs"""
        if not getattr(self, '_import_filename', None):
            audit_log = TaxLotAuditLog.objects.filter(
                view_id=self.pk).order_by('created').first()
            self._import_filename = audit_log.import_filename
        return self._import_filename


class TaxLotAuditLog(models.Model):
    organization = models.ForeignKey(Organization)
    parent1 = models.ForeignKey('TaxLotAuditLog', blank=True, null=True,
                                related_name='taxlotauditlog__parent1')
    parent2 = models.ForeignKey('TaxLotAuditLog', blank=True, null=True,
                                related_name='taxlotauditlog__parent2')
    state = models.ForeignKey('TaxLotState',
                              related_name='taxlotauditlog__state')
    view = models.ForeignKey('TaxLotView', related_name='taxlotauditlog__view',
                             null=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    import_filename = models.CharField(max_length=255, null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True,
                                      blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)
