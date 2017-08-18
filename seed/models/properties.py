# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import logging
import pdb

from django.contrib.postgres.fields import JSONField
from django.db import models

from auditlog import AUDIT_IMPORT
from auditlog import DATA_UPDATE_TYPE
from seed.data_importer.models import ImportFile
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    Cycle,
    StatusLabel,
    DATA_STATE,
    DATA_STATE_UNKNOWN,
    DATA_STATE_MATCHING,
    MERGE_STATE,
    MERGE_STATE_UNKNOWN,
    TaxLotProperty
)
from seed.utils.address import normalize_address_str
from seed.utils.generic import split_model_fields, obj_to_dict
from seed.utils.time import convert_datestr

_log = logging.getLogger(__name__)

# Oops! we override a builtin in some of the models
property_decorator = property


class Property(models.Model):
    """
    The Property is the parent property that ties together all the views of the property.
    For example, if a building has multiple changes overtime, then this Property will always
    remain the same. The PropertyView will point to the unchanged property as the PropertyState
    and Property view are updated.

    If the property can be a campus. The property can also reference a parent property.
    """
    organization = models.ForeignKey(Organization)

    # Handle properties that may have multiple properties (e.g. buildings)
    campus = models.BooleanField(default=False)
    parent_property = models.ForeignKey('Property', blank=True, null=True)
    labels = models.ManyToManyField(StatusLabel)

    class Meta:
        verbose_name_plural = 'properties'

    def __unicode__(self):
        return u'Property - %s' % (self.pk)


class PropertyState(models.Model):
    """Store a single property"""
    # Support finding the property by the import_file and source_type
    import_file = models.ForeignKey(ImportFile, null=True, blank=True)

    # FIXME: source_type needs to be a foreign key or make it import_file.source_type
    source_type = models.IntegerField(null=True, blank=True, db_index=True)

    organization = models.ForeignKey(Organization)
    data_state = models.IntegerField(choices=DATA_STATE, default=DATA_STATE_UNKNOWN)
    merge_state = models.IntegerField(choices=MERGE_STATE, default=MERGE_STATE_UNKNOWN, null=True)

    # Is this still being used during matching? Apparently so.
    confidence = models.FloatField(default=0, null=True, blank=True)

    jurisdiction_property_id = models.CharField(max_length=255, null=True, blank=True)

    custom_id_1 = models.CharField(max_length=255, null=True, blank=True)

    # If the property is a campus then the pm_parent_property_id is the same
    # for all the properties. The master campus record (campus=True on Property model) will
    # have the pm_property_id set to be the same as the pm_parent_property_id
    pm_parent_property_id = models.CharField(max_length=255, null=True, blank=True)
    pm_property_id = models.CharField(max_length=255, null=True, blank=True)

    home_energy_score_id = models.CharField(max_length=255, null=True, blank=True)

    # Tax Lot Number of the property - this field can be an unparsed list or just one string.
    lot_number = models.TextField(null=True, blank=True)
    property_name = models.CharField(max_length=255, null=True, blank=True)

    # Leave this as is for now, normalize into its own table soon
    # use properties to assess from instances
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    normalized_address = models.CharField(max_length=255, null=True, blank=True, editable=False)

    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)

    # Only spot where it's 'building' in the app, b/c this is a PM field.
    building_count = models.IntegerField(null=True, blank=True)

    property_notes = models.TextField(null=True, blank=True)
    property_type = models.TextField(null=True, blank=True)
    year_ending = models.DateField(null=True, blank=True)

    # Tax IDs are often stuck here.
    use_description = models.CharField(max_length=255, null=True, blank=True)

    gross_floor_area = models.FloatField(null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)
    recent_sale_date = models.DateTimeField(null=True, blank=True)
    conditioned_floor_area = models.FloatField(null=True, blank=True)
    occupied_floor_area = models.FloatField(null=True, blank=True)

    # Normalize eventually on owner/address table
    owner = models.CharField(max_length=255, null=True, blank=True)
    owner_email = models.CharField(max_length=255, null=True, blank=True)
    owner_telephone = models.CharField(max_length=255, null=True, blank=True)
    owner_address = models.CharField(max_length=255, null=True, blank=True)
    owner_city_state = models.CharField(max_length=255, null=True, blank=True)
    owner_postal_code = models.CharField(max_length=255, null=True, blank=True)

    energy_score = models.IntegerField(null=True, blank=True)
    site_eui = models.FloatField(null=True, blank=True)
    generation_date = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)
    source_eui_weather_normalized = models.FloatField(null=True, blank=True)
    site_eui_weather_normalized = models.FloatField(null=True, blank=True)
    source_eui = models.FloatField(null=True, blank=True)
    energy_alerts = models.TextField(null=True, blank=True)
    space_alerts = models.TextField(null=True, blank=True)
    building_certification = models.CharField(max_length=255, null=True, blank=True)

    extra_data = JSONField(default=dict, blank=True)

    class Meta:
        index_together = [
            ['import_file', 'data_state'],
            ['import_file', 'data_state', 'merge_state']
        ]

    def promote(self, cycle):
        """
        Promote the PropertyState to the view table for the given cycle

        Args:
            cycle: Cycle to assign the view

        Returns:
            The resulting PropertyView (note that it is not returning the
            PropertyState)

        """

        # First check if the cycle and the PropertyState already have a view
        pvs = PropertyView.objects.filter(cycle=cycle, state=self)

        if len(pvs) == 0:
            _log.debug("Found 0 PropertyViews, adding property, promoting")
            # There are no PropertyViews for this property state and cycle.
            # Most likely there is nothing to match right now, so just
            # promote it to the view

            # Need to create a property for this state
            if self.organization is None:
                _log.debug("organization is None")

            if not self.organization:
                pdb.set_trace()

            prop = Property.objects.create(organization=self.organization)

            pv = PropertyView.objects.create(property=prop, cycle=cycle, state=self)

            # This may be legacy and is definitely still needed here to have the tests pass.
            self.data_state = DATA_STATE_MATCHING
            self.save()

            return pv
        elif len(pvs) == 1:
            _log.debug("Found 1 PropertyView... Nothing to do")
            # PropertyView already exists for cycle and state. Nothing to do.

            return pvs[0]
        else:
            _log.debug("Found %s PropertyView" % len(pvs))
            _log.debug("This should never occur, famous last words?")

            return None

    def __unicode__(self):
        return u'Property State - %s' % self.pk

    def clean(self):
        date_field_names = (
            'year_ending',
            'generation_date',
            'release_date',
            'recent_sale_date'
        )
        for field in date_field_names:
            value = getattr(self, field)
            if value and isinstance(value, (str, unicode)):
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
        # Calculate and save the normalized address
        if self.address_line_1 is not None:
            self.normalized_address = normalize_address_str(self.address_line_1)
        else:
            self.normalized_address = None

        return super(PropertyState, self).save(*args, **kwargs)

    @classmethod
    def coparent(cls, state_id):
        """
        Return the coparent of the PropertyState. This will query the PropertyAuditLog table to
        determine if there is a coparent and return it if it is found. The state_id needs to be
        the base ID of when the original record was imported

        :param state_id: integer, state id to find coparent.
        :return: dict
        """

        coparents = list(
            PropertyState.objects.raw("""
                WITH creation_id AS (
                    SELECT
                      pal.id,
                      pal.state_id AS original_state_id
                    FROM seed_propertyauditlog pal
                    WHERE pal.state_id = %s AND
                          pal.name = 'Import Creation' AND
                          pal.import_filename IS NOT NULL
                ), audit_id AS (
                    SELECT
                      audit_log.id,
                      audit_log.state_id,
                      audit_log.parent1_id,
                      audit_log.parent2_id,
                      audit_log.parent_state1_id,
                      audit_log.parent_state2_id,
                      cid.original_state_id
                    FROM creation_id cid, seed_propertyauditlog audit_log
                    WHERE audit_log.parent1_id = cid.id OR audit_log.parent2_id = cid.id
                )
                SELECT
                    ps.id,
                    ps.pm_property_id,
                    ps.pm_parent_property_id,
                    ps.custom_id_1,
                    ps.address_line_1,
                    ps.address_line_2,
                    ps.city,
                    ps.state,
                    ps.postal_code,
                    ps.lot_number,
                    ps.gross_floor_area,
                    ps.use_description,
                    ps.energy_score,
                    ps.site_eui,
                    ps.property_notes,
                    ps.property_type,
                    ps.year_ending,
                    ps.owner,
                    ps.owner_email,
                    ps.owner_telephone,
                    ps.building_count,
                    ps.year_built,
                    ps.recent_sale_date,
                    ps.conditioned_floor_area,
                    ps.occupied_floor_area,
                    ps.owner_address,
                    ps.owner_postal_code,
                    ps.home_energy_score_id,
                    ps.generation_date,
                    ps.release_date,
                    ps.source_eui_weather_normalized,
                    ps.site_eui_weather_normalized,
                    ps.source_eui,
                    ps.energy_alerts,
                    ps.space_alerts,
                    ps.building_certification,
                    NULL
                FROM seed_propertystate ps, audit_id aid
                WHERE (ps.id = aid.parent_state1_id AND
                       aid.parent_state1_id <> aid.original_state_id) OR
                      (ps.id = aid.parent_state2_id AND
                       aid.parent_state2_id <> aid.original_state_id);""", [int(state_id)])
        )

        # reduce this down to just the fields that were returns and convert to dict. This is
        # important because the fields that were not queried will be deferred and require a new
        # query to retrieve.
        keep_fields = ['id', 'pm_property_id', 'pm_parent_property_id', 'custom_id_1',
                       'address_line_1', 'address_line_2', 'city', 'state', 'postal_code',
                       'lot_number', 'gross_floor_area', 'use_description', 'energy_score',
                       'site_eui', 'property_notes', 'property_type', 'year_ending', 'owner',
                       'owner_email', 'owner_telephone', 'building_count', 'year_built',
                       'recent_sale_date', 'conditioned_floor_area', 'occupied_floor_area',
                       'owner_address', 'owner_postal_code', 'home_energy_score_id',
                       'generation_date', 'release_date', 'source_eui_weather_normalized',
                       'site_eui_weather_normalized', 'source_eui',
                       'energy_alerts', 'space_alerts', 'building_certification', ]
        coparents = [{key: getattr(c, key) for key in keep_fields} for c in coparents]

        return coparents, len(coparents)


class PropertyView(models.Model):
    """
    Similar to the old world of canonical building.

    A PropertyView contains a reference to a property (which should not change) and to a
    cycle (time period), and a state (characteristics).

    """
    # different property views can be associated with each other (2012, 2013)
    property = models.ForeignKey(Property, related_name='views',
                                 on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT)
    state = models.ForeignKey(PropertyState, on_delete=models.CASCADE)

    def __unicode__(self):
        return u'Property View - %s' % self.pk

    class Meta:
        unique_together = ('property', 'cycle',)
        index_together = [['state', 'cycle']]

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

    def tax_lot_views(self):
        """
        Return a list of TaxLotViews that are associated with this PropertyView and Cycle

        :return: list of TaxLotViews
        """
        # forwent the use of list comprehension to make the code more readable.
        # get the related taxlot_view.state as well to save time if needed.
        result = []
        for tlp in TaxLotProperty.objects.filter(
                cycle=self.cycle,
                property_view=self).select_related('taxlot_view', 'taxlot_view__state'):
            result.append(tlp.taxlot_view)

        return result

    def tax_lot_states(self):
        """
        Return a list of TaxLotStates associated with this PropertyView and Cycle

        :return: list of TaxLotStates
        """
        # forwent the use of list comprehension to make the code more readable.
        result = []
        for x in self.tax_lot_views():
            if x.state:
                result.append(x.state)

        return result

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
    parent1 = models.ForeignKey('PropertyAuditLog', blank=True, null=True,
                                related_name='propertyauditlog__parent1')
    parent2 = models.ForeignKey('PropertyAuditLog', blank=True, null=True,
                                related_name='propertyauditlog__parent2')

    # store the parent states as well so that we can quickly return which state is associated
    # with the parents of the audit log without having to query the parent audit log to grab
    # the state
    parent_state1 = models.ForeignKey(PropertyState, blank=True, null=True,
                                      related_name='propertyauditlog__parent_state1')
    parent_state2 = models.ForeignKey(PropertyState, blank=True, null=True,
                                      related_name='propertyauditlog__parent_state2')

    state = models.ForeignKey('PropertyState', related_name='propertyauditlog__state')
    view = models.ForeignKey('PropertyView', related_name='propertyauditlog__view', null=True)

    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    import_filename = models.CharField(max_length=255, null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        index_together = [['state', 'name'], ['parent_state1', 'parent_state2']]
