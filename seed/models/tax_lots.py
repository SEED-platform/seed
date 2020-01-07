# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import re
from os import path

from django.contrib.gis.db import models as geomodels
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver

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
from seed.utils.generic import (
    compare_orgs_between_label_and_target,
    split_model_fields,
    obj_to_dict,
)
from seed.utils.time import convert_to_js_timestamp
from .auditlog import AUDIT_IMPORT
from .auditlog import DATA_UPDATE_TYPE

_log = logging.getLogger(__name__)


class TaxLot(models.Model):
    # NOTE: we have been calling this the organization. We
    # should stay consistent although I prefer the name organization (!super_org)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    # Track when the entry was created and when it was updated
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'TaxLot - %s' % self.pk


class TaxLotState(models.Model):
    # The state field names should match pretty close to the pdf, just
    # because these are the most 'public' fields in terms of
    # communicating with the cities.

    # Support finding the property by the import_file
    import_file = models.ForeignKey(ImportFile, on_delete=models.CASCADE, null=True, blank=True)

    # Add organization to the tax lot states
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    data_state = models.IntegerField(choices=DATA_STATE, default=DATA_STATE_UNKNOWN)
    merge_state = models.IntegerField(choices=MERGE_STATE, default=MERGE_STATE_UNKNOWN, null=True)

    custom_id_1 = models.CharField(max_length=255, null=True, blank=True)

    jurisdiction_tax_lot_id = models.CharField(max_length=2047, null=True, blank=True)
    block_number = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=255, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    normalized_address = models.CharField(max_length=255, null=True, blank=True, editable=False)

    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=255, null=True, blank=True)
    number_properties = models.IntegerField(null=True, blank=True)

    extra_data = JSONField(default=dict, blank=True)
    hash_object = models.CharField(max_length=32, null=True, blank=True, default=None)

    # taxlots can now have lat/long and polygons, points.
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    long_lat = geomodels.PointField(geography=True, null=True, blank=True)
    centroid = geomodels.PolygonField(geography=True, null=True, blank=True)
    bounding_box = geomodels.PolygonField(geography=True, null=True, blank=True)
    taxlot_footprint = geomodels.PolygonField(geography=True, null=True, blank=True)
    # A unique building identifier as defined by DOE's UBID project (https://buildingid.pnnl.gov/)
    # Note that ulid is not an actual project at the moment, but it is similar to UBID in that it
    # is a unique string that represents the bounding box of the Land (or Lot)
    ulid = models.CharField(max_length=255, null=True, blank=True)

    geocoding_confidence = models.CharField(max_length=32, null=True, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        index_together = [
            ['hash_object'],
            ['import_file', 'data_state'],
            ['import_file', 'data_state', 'merge_state']
        ]

    def __str__(self):
        return 'TaxLot State - %s' % self.pk

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
            # _log.debug("Found 0 TaxLotViews, adding TaxLot, promoting")
            # There are no PropertyViews for this property state and cycle.
            # Most likely there is nothing to match right now, so just
            # promote it to the view

            # Need to create a property for this state
            if self.organization is None:
                _log.error("organization is None")

            taxlot = TaxLot.objects.create(organization=self.organization)

            tlv = TaxLotView.objects.create(taxlot=taxlot, cycle=cycle, state=self)

            # This is legacy but still needed here to have the tests pass.
            self.data_state = DATA_STATE_MATCHING

            self.save()

            return tlv
        elif len(tlvs) == 1:
            # _log.debug("Found 1 PropertyView... Nothing to do")
            # PropertyView already exists for cycle and state. Nothing to do.

            return tlvs[0]
        else:
            _log.error("Found %s PropertyView" % len(tlvs))
            _log.error("This should never occur, famous last words?")

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
            ed_fields = list(filter(lambda f: f in extra_data, ed_fields))

            result = {
                field: getattr(self, field) for field in model_fields
            }
            result['extra_data'] = {
                field: extra_data[field] for field in ed_fields
            }

            # always return id's
            result['id'] = result['pk'] = self.pk

            return result

        d = obj_to_dict(self, include_m2m=include_related_data)

        return d

    def save(self, *args, **kwargs):
        # Calculate and save the normalized address
        if self.address_line_1 is not None:
            self.normalized_address = normalize_address_str(self.address_line_1)
        else:
            self.normalized_address = None

        # save a hash of the object to the database for quick lookup
        from seed.data_importer.tasks import hash_state_object
        self.hash_object = hash_state_object(self)
        return super().save(*args, **kwargs)

    def history(self):
        """
        Return the history of the taxlot state by parsing through the auditlog. Returns only the ids
        of the parent states and some descriptions.

              master
              /    \
             /      \
          parent1  parent2

        In the records, parent2 is most recent, so make sure to navigate parent two first since we
        are returning the data in reverse over (that is most recent changes first)

        :return: list, history as a list, and the master record
        """

        """Return history in reverse order."""
        history = []
        master = {
            'state_id': self.id,
            'state_data': self,
            'date_edited': None,
        }

        def record_dict(log):
            filename = None if not log.import_filename else path.basename(log.import_filename)
            if filename:
                # Attempt to remove NamedTemporaryFile suffix
                name, ext = path.splitext(filename)
                pattern = re.compile('(.*?)(_[a-zA-Z0-9]{7})$')
                match = pattern.match(name)
                if match:
                    filename = match.groups()[0] + ext
            return {
                'state_id': log.state.id,
                'state_data': log.state,
                'date_edited': convert_to_js_timestamp(log.created),
                'source': log.get_record_type_display(),
                'filename': filename,
                # 'changed_fields': json.loads(log.description) if log.record_type == AUDIT_USER_EDIT else None
            }

        log = TaxLotAuditLog.objects.select_related('state', 'parent1', 'parent2').filter(
            state_id=self.id
        ).order_by('-id').first()

        if log:
            master = {
                'state_id': log.state.id,
                'state_data': log.state,
                'date_edited': convert_to_js_timestamp(log.created),
            }

            # Traverse parents and add to history
            if log.name in ['Manual Match', 'System Match', 'Merge current state in migration']:
                done_searching = False

                while not done_searching:
                    # if there is no parents, then break out immediately
                    if (
                            log.parent1_id is None and log.parent2_id is None) or log.name == 'Manual Edit':
                        break

                    # initalize the tree to None everytime. If not new tree is found, then we will not iterate
                    tree = None

                    # Check if parent2 has any other parents or is the original import creation. Start with parent2
                    # because parent2 will be the most recent import file.
                    if log.parent2:
                        if log.parent2.name in ['Import Creation', 'Manual Edit']:
                            record = record_dict(log.parent2)
                            history.append(record)
                        elif log.parent2.name == 'System Match' and log.parent2.parent1.name == 'Import Creation' and log.parent2.parent2.name == 'Import Creation':
                            # Handle case where an import file matches within itself, and proceeds to match with
                            # existing records
                            record = record_dict(log.parent2.parent2)
                            history.append(record)
                            record = record_dict(log.parent2.parent1)
                            history.append(record)
                        else:
                            tree = log.parent2

                    if log.parent1:
                        if log.parent1.name in ['Import Creation', 'Manual Edit']:
                            record = record_dict(log.parent1)
                            history.append(record)
                        elif log.parent1.name == 'System Match' and log.parent1.parent1.name == 'Import Creation' and log.parent1.parent2.name == 'Import Creation':
                            # Handle case where an import file matches within itself, and proceeds to match with
                            # existing records
                            record = record_dict(log.parent1.parent2)
                            history.append(record)
                            record = record_dict(log.parent1.parent1)
                            history.append(record)
                        else:
                            tree = log.parent1

                    if not tree:
                        done_searching = True
                    else:
                        log = tree
            elif log.name == 'Manual Edit':
                record = record_dict(log.parent1)
                history.append(record)
            elif log.name == 'Import Creation':
                record = record_dict(log)
                history.append(record)

        return history, master

    @classmethod
    def coparent(cls, state_id):
        """
        Return the coparent of the TaxLotState. This will query the TaxLotAuditLog table to
        determine if there is a coparent and return it if it is found. The state_id needs to be
        the base ID of when the original record was imported

        :param state_id: integer, state id to find coparent.
        :return: dict
        """

        coparents = list(
            TaxLotState.objects.raw("""
                    WITH creation_id AS (
                        SELECT
                          pal.id,
                          pal.state_id AS original_state_id
                        FROM seed_taxlotauditlog pal
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
                        FROM creation_id cid, seed_taxlotauditlog audit_log
                        WHERE audit_log.parent1_id = cid.id OR audit_log.parent2_id = cid.id
                    )
                    SELECT
                      ps.id,
                      ps.custom_id_1,
                      ps.block_number,
                      ps.district,
                      ps.address_line_1,
                      ps.address_line_2,
                      ps.city,
                      ps.state,
                      ps.postal_code,
                      ps.extra_data,
                      ps.number_properties,
                      ps.jurisdiction_tax_lot_id,
                      ps.geocoding_confidence,
                      NULL
                    FROM seed_taxlotstate ps, audit_id aid
                    WHERE (ps.id = aid.parent_state1_id AND
                           aid.parent_state1_id <> aid.original_state_id) OR
                          (ps.id = aid.parent_state2_id AND
                           aid.parent_state2_id <> aid.original_state_id);""", [int(state_id)])
        )

        # reduce this down to just the fields that were returns and convert to dict. This is
        # important because the fields that were not queried will be deferred and require a new
        # query to retrieve.
        keep_fields = ['id', 'custom_id_1', 'jurisdiction_tax_lot_id', 'block_number', 'district',
                       'address_line_1', 'address_line_2', 'city', 'state', 'postal_code',
                       'number_properties', 'extra_data']
        coparents = [{key: getattr(c, key) for key in keep_fields} for c in coparents]

        return coparents, len(coparents)

    @classmethod
    def merge_relationships(cls, merged_state, state1, state2):
        """Stub to implement if merging TaxLotState relationships is needed"""
        return None


class TaxLotView(models.Model):
    taxlot = models.ForeignKey(TaxLot, on_delete=models.CASCADE, related_name='views', null=True)
    state = models.ForeignKey(TaxLotState, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT)

    labels = models.ManyToManyField(StatusLabel)

    def __str__(self):
        return 'TaxLot View - %s' % self.pk

    class Meta:
        unique_together = ('taxlot', 'cycle',)
        index_together = [['state', 'cycle']]

    def __init__(self, *args, **kwargs):
        self._import_filename = kwargs.pop('import_filename', None)
        super().__init__(*args, **kwargs)

    def initialize_audit_logs(self, **kwargs):
        kwargs.update({
            'organization': self.taxlot.organization,
            'state': self.state,
            'view': self,
            'record_type': AUDIT_IMPORT
        })
        return TaxLotAuditLog.objects.create(**kwargs)

    def property_views(self):
        """
        Return a list of PropertyViews that are associated with this TaxLotView and Cycle

        :return: list of PropertyViews
        """

        # forwent the use of list comprehension to make the code more readable.
        # get the related property_view__state as well to save time, if needed.
        result = []
        for tlp in TaxLotProperty.objects.filter(cycle=self.cycle, taxlot_view=self).select_related(
                'property_view', 'property_view__state'):
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


@receiver(post_save, sender=TaxLotView)
def post_save_taxlot_view(sender, **kwargs):
    """
    When changing/saving the TaxLotView, go ahead and touch the TaxLot (if linked) so that the record
    receives an updated datetime
    """
    if kwargs['instance'].taxlot:
        kwargs['instance'].taxlot.save()


class TaxLotAuditLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    parent1 = models.ForeignKey('TaxLotAuditLog', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='taxlotauditlog_parent1')
    parent2 = models.ForeignKey('TaxLotAuditLog', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='taxlotauditlog_parent2')

    # store the parent states as well so that we can quickly return which state is associated
    # with the parents of the audit log without having to query the parent audit log to grab
    # the state
    parent_state1 = models.ForeignKey(TaxLotState, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='taxlotauditlog_parent_state1')
    parent_state2 = models.ForeignKey(TaxLotState, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='taxlotauditlog_parent_state2')

    state = models.ForeignKey('TaxLotState', on_delete=models.CASCADE,
                              related_name='taxlotauditlog_state')
    view = models.ForeignKey('TaxLotView', on_delete=models.CASCADE, related_name='taxlotauditlog_view',
                             null=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    import_filename = models.CharField(max_length=255, null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True,
                                      blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        index_together = [['state', 'name'], ['parent_state1', 'parent_state2']]


@receiver(pre_save, sender=TaxLotState)
def sync_latitude_longitude_and_long_lat(sender, instance, **kwargs):
    try:
        original_obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass  # Occurs on object creation
    else:
        # Sync Latitude, Longitude, and long_lat fields if applicable
        latitude_change = original_obj.latitude != instance.latitude
        longitude_change = original_obj.longitude != instance.longitude
        long_lat_change = original_obj.long_lat != instance.long_lat
        lat_and_long_both_populated = instance.latitude is not None and instance.longitude is not None

        # The 'not long_lat_change' condition removes the case when long_lat is changed by an external API
        if (latitude_change or longitude_change) and lat_and_long_both_populated and not long_lat_change:
            instance.long_lat = f"POINT ({instance.longitude} {instance.latitude})"
            instance.geocoding_confidence = "Manually geocoded (N/A)"
        elif (latitude_change or longitude_change) and not lat_and_long_both_populated:
            instance.long_lat = None
            instance.geocoding_confidence = None


m2m_changed.connect(compare_orgs_between_label_and_target, sender=TaxLotView.labels.through)
