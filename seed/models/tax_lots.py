# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import logging

from django.db import models
from django_pgjson.fields import JsonField

from auditlog import AUDIT_IMPORT
from auditlog import DATA_UPDATE_TYPE
from seed.data_importer.models import ImportFile
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Cycle,
    StatusLabel,
    TaxLotProperty,
    DATA_STATE,
    DATA_STATE_UNKNOWN,
    DATA_STATE_MATCHING,
    MERGE_STATE,
    MERGE_STATE_UNKNOWN,
)
from seed.utils.address import normalize_address_str
from seed.utils.generic import split_model_fields, obj_to_dict

logger = logging.getLogger(__name__)


class TaxLot(models.Model):
    # NOTE: we have been calling this the organization. We
    # should stay consistent although I prefer the name organization (!super_org)
    organization = models.ForeignKey(Organization)
    labels = models.ManyToManyField(StatusLabel)

    def __unicode__(self):
        return u'TaxLot - %s' % (self.pk)


class TaxLotState(models.Model):
    # The state field names should match pretty close to the pdf, just
    # because these are the most 'public' fields in terms of
    # communicating with the cities.

    confidence = models.FloatField(default=0, null=True, blank=True)

    # Support finding the property by the import_file
    import_file = models.ForeignKey(ImportFile, null=True, blank=True)

    # Add organization to the tax lot states
    organization = models.ForeignKey(Organization)
    data_state = models.IntegerField(choices=DATA_STATE, default=DATA_STATE_UNKNOWN)
    merge_state = models.IntegerField(choices=MERGE_STATE, default=MERGE_STATE_UNKNOWN, null=True)

    custom_id_1 = models.CharField(max_length=255, null=True, blank=True)

    jurisdiction_tax_lot_id = models.CharField(max_length=2047, null=True, blank=True)
    block_number = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=255, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    normalized_address = models.CharField(max_length=255, null=True, blank=True, editable=False)

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
            Promote the TaxLotState to the view table for the given cycle

            Args:
                cycle: Cycle to assign the view

            Returns:
                The resulting TaxLotView (note that it is not returning the
                TaxLotState)

        """
        # First check if the cycle and the PropertyState already have a view
        tlvs = TaxLotView.objects.filter(cycle=cycle, state=self)

        if len(tlvs) == 0:
            logger.debug("Found 0 TaxLotViews, adding TaxLot, promoting")
            # There are no PropertyViews for this property state and cycle.
            # Most likely there is nothing to match right now, so just
            # promote it to the view

            # Need to create a property for this state
            if self.organization is None:
                print "organization is None"  # TODO: raise an exception

            taxlot = TaxLot.objects.create(
                organization=self.organization
            )

            tlv = TaxLotView.objects.create(taxlot=taxlot, cycle=cycle, state=self)

            # This is legacy but still needed here to have the tests pass.
            self.data_state = DATA_STATE_MATCHING

            self.save()

            return tlv
        elif len(tlvs) == 1:
            logger.debug("Found 1 PropertyView... Nothing to do")
            # PropertyView already exists for cycle and state. Nothing to do.

            return tlvs[0]
        else:
            logger.debug("Found %s PropertyView" % len(tlvs))
            logger.debug("This should never occur, famous last words?")

            return None

    def to_dict(self, fields=None, include_related_data=True):
        """
        Returns a dict version of the TaxLotState, either with all fields
        or masked to just those requested.
        """

        # TODO: make this a serializer and/or merge with PropertyState.to_dict
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

    def save(self, *args, **kwargs):
        # TODO: Check with Nick on this - this is totally incorrect.

        # first check if the jurisdiction_tax_lot_id isn't already in the database for the
        # organization - potential todo--move this to a unique constraint of the db.
        # TODO: Decide if we should allow the user to define what the unique ID is for the taxlot
        # if TaxLotState.objects.filter(jurisdiction_tax_lot_id=self.jurisdiction_tax_lot_id,
        #                               organization=self.organization).exists():
        #     logger.error("TaxLotState already exists for the same jurisdiction_tax_lot_id and org")
        #     return False
        # Calculate and save the normalized address
        if self.address_line_1 is not None:
            self.normalized_address = normalize_address_str(self.address_line_1)
        else:
            self.normalized_address = None

        return super(TaxLotState, self).save(*args, **kwargs)


class TaxLotView(models.Model):
    # TODO: Are all foreign keys automatically indexed?
    taxlot = models.ForeignKey(TaxLot, related_name='views', null=True)
    state = models.ForeignKey(TaxLotState)
    cycle = models.ForeignKey(Cycle)

    # labels = models.ManyToManyField(StatusLabel)

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

    def property_views(self):
        """
        Return a list of PropertyViews that are associated with this TaxLotView and Cycle

        :return: list of PropertyViews
        """

        # forwent the use of list comprehension to make the code more readable.
        # get the related property_view__state as well to save time, if needed.
        result = []
        for tlp in TaxLotProperty.objects.filter(
                cycle=self.cycle,
                taxlot_view=self).select_related('property_view', 'property_view__state'):
            if tlp.taxlot_view:
                result.append(tlp.property_view)

        return result

    def property_states(self):
        """
        Return a list of PropertyStates associated with this TaxLotView and Cycle

        :return: list of PropertyStates
        """
        # forwent the use of list comprehension to make the code more readable.
        result = []
        for x in self.property_views():
            if x.state:
                result.append(x.state)

        return result

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
