# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import copy
import logging
import re
from os import path

from django.contrib.gis.db import models as geomodels
from django.contrib.postgres.fields import JSONField
from django.db import (
    models,
    transaction,
    IntegrityError,
)
from django.db.models.signals import pre_delete, pre_save, post_save, m2m_changed
from django.dispatch import receiver
from django.forms.models import model_to_dict
from past.builtins import basestring
from quantityfield.fields import QuantityField

from seed.data_importer.models import ImportFile
# from seed.utils.cprofile import cprofile
from seed.lib.mcm.cleaners import date_cleaner
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
from seed.utils.generic import (
    compare_orgs_between_label_and_target,
    split_model_fields,
    obj_to_dict,
)
from seed.utils.time import convert_datestr
from seed.utils.time import convert_to_js_timestamp
from .auditlog import AUDIT_IMPORT
from .auditlog import DATA_UPDATE_TYPE

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
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    # Handle properties that may have multiple properties (e.g. buildings)
    campus = models.BooleanField(default=False)
    parent_property = models.ForeignKey('Property', on_delete=models.CASCADE, blank=True, null=True)

    # Track when the entry was created and when it was updated
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'properties'

    def __str__(self):
        return 'Property - %s' % (self.pk)

    def copy_meters(self, source_property_id, source_persists=True):
        """
        Copies meters from a source Property to the current Property.

        It's most efficient if the persistence of the source Property's readings
        aren't needed as bulk reassignments can then be used.

        The cases and logic are described in comments throughout.
        """
        source_property = Property.objects.get(pk=source_property_id)

        # If the source property has no meters to copy, there's nothing to do.
        if not source_property.meters.exists():
            return

        if self.meters.exists() is False and source_persists is False:
            # In this case, simply copy over the meters and readings from source in bulk.
            source_property.meters.update(property_id=self.id)
        else:
            # In any other case, copy over the readings from source one meter at
            # a time, checking to see if self has a similar meter each time.
            # Note that we only copy meters not linked to scenarios because it's assumed
            # the property has already gone through merge_relationships()
            for source_meter in source_property.meters.filter(scenario_id=None):
                with transaction.atomic():
                    target_meter, created = self.meters.get_or_create(
                        is_virtual=source_meter.is_virtual,
                        source=source_meter.source,
                        source_id=source_meter.source_id,
                        type=source_meter.type
                    )

                    if created:
                        # If self didn't have a similar meter and a new one was created,
                        # decide what to do depending on whether source meters need to persist.
                        if source_persists:
                            # Note, overlaps aren't possible since a new meter was created.
                            target_meter.copy_readings(source_meter, overlaps_possible=False)
                        else:
                            source_meter.meter_readings.update(meter=target_meter)
                    else:
                        # If self did have a similar meter, copy readings assuming overlaps are possible.
                        target_meter.copy_readings(source_meter, overlaps_possible=True)


class PropertyState(models.Model):
    """Store a single property. This contains all the state information about the property"""
    ANALYSIS_STATE_NOT_STARTED = 0
    ANALYSIS_STATE_STARTED = 1
    ANALYSIS_STATE_COMPLETED = 2
    ANALYSIS_STATE_FAILED = 3
    ANALYSIS_STATE_QUEUED = 4  # analysis queue was added after the others above.

    ANALYSIS_STATE_TYPES = (
        (ANALYSIS_STATE_NOT_STARTED, 'Not Started'),
        (ANALYSIS_STATE_QUEUED, 'Queued'),
        (ANALYSIS_STATE_STARTED, 'Started'),
        (ANALYSIS_STATE_COMPLETED, 'Completed'),
        (ANALYSIS_STATE_FAILED, 'Failed'),
    )

    # Support finding the property by the import_file and source_type
    import_file = models.ForeignKey(ImportFile, on_delete=models.CASCADE, null=True, blank=True)

    # FIXME: source_type needs to be a foreign key or make it import_file.source_type
    source_type = models.IntegerField(null=True, blank=True, db_index=True)

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    data_state = models.IntegerField(choices=DATA_STATE, default=DATA_STATE_UNKNOWN)
    merge_state = models.IntegerField(choices=MERGE_STATE, default=MERGE_STATE_UNKNOWN, null=True)

    jurisdiction_property_id = models.TextField(null=True, blank=True)

    custom_id_1 = models.CharField(max_length=255, null=True, blank=True)

    # A unique building identifier as defined by DOE's UBID project (https://buildingid.pnnl.gov/)
    ubid = models.CharField(max_length=255, null=True, blank=True)

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

    # New fields for latitude and longitude as native database objects
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    long_lat = geomodels.PointField(geography=True, null=True, blank=True)
    centroid = geomodels.PolygonField(geography=True, null=True, blank=True)
    bounding_box = geomodels.PolygonField(geography=True, null=True, blank=True)
    property_footprint = geomodels.PolygonField(geography=True, null=True, blank=True)

    # footprint = geomodels.PolygonField(geography=True, null=True, blank=True)
    geocoding_confidence = models.CharField(max_length=32, null=True, blank=True)

    # Only spot where it's 'building' in the app, b/c this is a PM field.
    building_count = models.IntegerField(null=True, blank=True)

    property_notes = models.TextField(null=True, blank=True)
    property_type = models.TextField(null=True, blank=True)
    year_ending = models.DateField(null=True, blank=True)

    # Tax IDs are often stuck here.
    use_description = models.CharField(max_length=255, null=True, blank=True)

    year_built = models.IntegerField(null=True, blank=True)
    recent_sale_date = models.DateTimeField(null=True, blank=True)

    # Normalize eventually on owner/address table
    owner = models.CharField(max_length=255, null=True, blank=True)
    owner_email = models.CharField(max_length=255, null=True, blank=True)
    owner_telephone = models.CharField(max_length=255, null=True, blank=True)
    owner_address = models.CharField(max_length=255, null=True, blank=True)
    owner_city_state = models.CharField(max_length=255, null=True, blank=True)
    owner_postal_code = models.CharField(max_length=255, null=True, blank=True)

    generation_date = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)

    energy_score = models.IntegerField(null=True, blank=True)

    energy_alerts = models.TextField(null=True, blank=True)
    space_alerts = models.TextField(null=True, blank=True)
    building_certification = models.CharField(max_length=255, null=True, blank=True)

    analysis_start_time = models.DateTimeField(null=True)
    analysis_end_time = models.DateTimeField(null=True)
    analysis_state = models.IntegerField(choices=ANALYSIS_STATE_TYPES,
                                         default=ANALYSIS_STATE_NOT_STARTED,
                                         null=True)
    analysis_state_message = models.TextField(null=True)

    # Need to add another field eventually to define the source of the EUI's and other
    # reported fields. Ideally would have the ability to provide the same field from
    # multiple data sources. For example, site EUI (portfolio manager), site EUI (calculated),
    # site EUI (modeled 8/4/2017).
    #
    # note: `*_orig` are all the unit-unaware original fields in the property
    # state, which have been superceded by unit-aware Quantity fields. The old
    # ones are left in place via the rename from eg. site_eui -> site_eui_orig
    # with their original data intact until we're sure things are OK with the
    # new columns. At that point (probably 2.4 release) these can be safely
    # deleted and removed with a migration.

    # old pre-Quantity columns

    gross_floor_area_orig = models.FloatField(null=True, blank=True)
    conditioned_floor_area_orig = models.FloatField(null=True, blank=True)
    occupied_floor_area_orig = models.FloatField(null=True, blank=True)
    site_eui_orig = models.FloatField(null=True, blank=True)
    site_eui_weather_normalized_orig = models.FloatField(null=True, blank=True)
    site_eui_modeled_orig = models.FloatField(null=True, blank=True)
    source_eui_orig = models.FloatField(null=True, blank=True)
    source_eui_weather_normalized_orig = models.FloatField(null=True, blank=True)
    source_eui_modeled_orig = models.FloatField(null=True, blank=True)

    # new Quantity columns

    gross_floor_area = QuantityField('ft**2', null=True, blank=True)
    conditioned_floor_area = QuantityField('ft**2', null=True, blank=True)
    occupied_floor_area = QuantityField('ft**2', null=True, blank=True)
    site_eui = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    site_eui_weather_normalized = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    site_eui_modeled = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    source_eui = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    source_eui_weather_normalized = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    source_eui_modeled = QuantityField('kBtu/ft**2/year', null=True, blank=True)

    extra_data = JSONField(default=dict, blank=True)
    hash_object = models.CharField(max_length=32, null=True, blank=True, default=None)
    measures = models.ManyToManyField('Measure', through='PropertyMeasure')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        index_together = [
            ['hash_object'],
            ['import_file', 'data_state'],
            ['import_file', 'data_state', 'merge_state'],
            ['import_file', 'data_state', 'source_type'],
            ['analysis_state', 'organization'],
        ]

    def promote(self, cycle, property_id=None):
        """
        Promote the PropertyState to the view table for the given cycle

        Args:
            cycle: Cycle to assign the view
            property_id: Optional ID of a canonical property model object
            to retain instead of creating a new property

        Returns:
            The resulting PropertyView (note that it is not returning the
            PropertyState)

        """

        # First check if the cycle and the PropertyState already have a view
        pvs = PropertyView.objects.filter(cycle=cycle, state=self)

        if len(pvs) == 0:
            # _log.debug("Found 0 PropertyViews, adding property, promoting")
            # There are no PropertyViews for this property state and cycle.
            # Most likely there is nothing to match right now, so just
            # promote it to the view

            # Need to create a property for this state
            if self.organization is None:
                _log.warn("organization is None")

            if property_id:
                try:
                    # should I validate this further?
                    prop = Property.objects.get(id=property_id)
                except Property.DoesNotExist:
                    _log.error("Could not promote this property")
                    return None
            else:
                prop = Property.objects.create(organization=self.organization)

            pv = PropertyView.objects.create(property=prop, cycle=cycle, state=self)

            # This may be legacy and is definitely still needed here to have the tests pass.
            self.data_state = DATA_STATE_MATCHING
            self.save()

            return pv
        elif len(pvs) == 1:
            # _log.debug("Found 1 PropertyView... Nothing to do")
            # PropertyView already exists for cycle and state. Nothing to do.

            return pvs[0]
        else:
            _log.error("Found %s PropertyView" % len(pvs))
            _log.error("This should never occur, famous last words?")

            return None

    def __str__(self):
        return 'Property State - %s' % self.pk

    def clean(self):
        date_field_names = (
            'year_ending',
            'generation_date',
            'release_date',
            'recent_sale_date'
        )
        for field in date_field_names:
            value = getattr(self, field)
            if value and isinstance(value, basestring):
                _log.info("Saving %s which is a date time" % field)
                _log.info(convert_datestr(value))
                _log.info(date_cleaner(value))

    def to_dict(self, fields=None, include_related_data=True):
        """
        Returns a dict version of the PropertyState, either with all fields
        or masked to just those requested.
        """
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
        Return the history of the property state by parsing through the auditlog. Returns only the ids
        of the parent states and some descriptions.

              master
              /   \
             /     \
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

        log = PropertyAuditLog.objects.select_related('state', 'parent1', 'parent2').filter(
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
                    if (log.parent1_id is None and log.parent2_id is None) or log.name == 'Manual Edit':
                        break

                    # initalize the tree to None everytime. If not new tree is found, then we will not iterate
                    tree = None

                    # Check if parent2 has any other parents or is the original import creation. Start with parent2
                    # because parent2 will be the most recent import file.
                    if log.parent2:
                        if log.parent2.name in ['Import Creation', 'Manual Edit']:
                            record = record_dict(log.parent2)
                            history.append(record)
                        elif log.parent2.name == 'System Match' and log.parent2.parent1.name == 'Import Creation' and \
                                log.parent2.parent2.name == 'Import Creation':
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
                        elif log.parent1.name == 'System Match' and log.parent1.parent1 and log.parent1.parent1.name == 'Import Creation' and \
                                log.parent1.parent2 and log.parent1.parent2.name == 'Import Creation':
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
                    ps.ubid,
                    ps.address_line_1,
                    ps.address_line_2,
                    ps.city,
                    ps.state,
                    ps.postal_code,
                    ps.longitude,
                    ps.latitude,
                    ps.geocoding_confidence,
                    ps.lot_number,
                    ps.gross_floor_area,
                    ps.use_description,
                    ps.energy_score,
                    ps.site_eui,
                    ps.site_eui_modeled,
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
                    ps.source_eui_modeled,
                    ps.energy_alerts,
                    ps.space_alerts,
                    ps.building_certification,
                    ps.analysis_start_time,
                    ps.analysis_end_time,
                    ps.analysis_state,
                    ps.analysis_state_message,
                    ps.extra_data,
                    NULL
                FROM seed_propertystate ps, audit_id aid
                WHERE (ps.id = aid.parent_state1_id AND
                       aid.parent_state1_id <> aid.original_state_id) OR
                      (ps.id = aid.parent_state2_id AND
                       aid.parent_state2_id <> aid.original_state_id);""", [int(state_id)])
        )

        # reduce this down to just the fields that were returned and convert to dict. This is
        # important because the fields that were not queried will be deferred and require a new
        # query to retrieve.
        keep_fields = ['id', 'pm_property_id', 'pm_parent_property_id', 'custom_id_1', 'ubid',
                       'address_line_1', 'address_line_2', 'city', 'state', 'postal_code',
                       'longitude', 'latitude',
                       'lot_number', 'gross_floor_area', 'use_description', 'energy_score',
                       'site_eui', 'site_eui_modeled', 'property_notes', 'property_type',
                       'year_ending', 'owner', 'owner_email', 'owner_telephone', 'building_count',
                       'year_built', 'recent_sale_date', 'conditioned_floor_area',
                       'occupied_floor_area', 'owner_address', 'owner_postal_code',
                       'home_energy_score_id', 'generation_date', 'release_date',
                       'source_eui_weather_normalized', 'site_eui_weather_normalized',
                       'source_eui', 'source_eui_modeled', 'energy_alerts', 'space_alerts',
                       'building_certification', 'analysis_start_time', 'analysis_end_time',
                       'analysis_state', 'analysis_state_message', 'extra_data', ]
        coparents = [{key: getattr(c, key) for key in keep_fields} for c in coparents]

        return coparents, len(coparents)

    @classmethod
    def merge_relationships(cls, merged_state, state1, state2):
        """
        Merge together the old relationships with the new.
        """
        from seed.models.simulations import Simulation
        from seed.models.property_measures import PropertyMeasure
        from seed.models.scenarios import Scenario

        # TODO: get some items off of this property view - labels and eventually notes

        # collect the relationships
        no_measure_scenarios = [x for x in state2.scenarios.filter(measures__isnull=True)]
        building_files = [x for x in state2.building_files.all()]
        simulations = [x for x in Simulation.objects.filter(property_state=state2)]
        measures = [x for x in PropertyMeasure.objects.filter(property_state=state2)]

        # copy in the no measure scenarios
        for new_s in no_measure_scenarios:
            source_scenario_id = new_s.pk
            new_s.pk = None
            new_s.save()
            merged_state.scenarios.add(new_s)

            # copy meters
            new_s.copy_initial_meters(source_scenario_id)

        for new_bf in building_files:
            # save the created and modified data from the original file
            orig_created = new_bf.created
            orig_modified = new_bf.modified
            new_bf.pk = None
            new_bf.save()
            new_bf.created = orig_created
            new_bf.modified = orig_modified
            new_bf.save()

            merged_state.building_files.add(new_bf)

        for new_sim in simulations:
            new_sim.pk = None
            new_sim.property_state = merged_state
            new_sim.save()

        if len(measures) > 0:
            measure_fields = [f.name for f in measures[0]._meta.fields]
            measure_fields.remove('id')
            measure_fields.remove('property_state')

            new_items = []

            # Create a list of scenarios and measures to reconstruct
            # {
            #   scenario_id_1: [ new_measure_id_1, new_measure_id_2 ],
            #   scenario_id_2: [ new_measure_id_2, new_measure_id_3 ],  # measure ids can be repeated
            # }
            scenario_measure_map = {}
            for measure in measures:
                test_dict = model_to_dict(measure, fields=measure_fields)

                if test_dict in new_items:
                    continue
                else:
                    try:
                        new_measure = copy.deepcopy(measure)
                        # copy the created and modifed time
                        new_measure.pk = None
                        new_measure.property_state = merged_state
                        new_measure.save()

                        # grab the scenario that is attached to the orig measure and create a new connection
                        for scenario in measure.scenario_set.all():
                            if scenario.pk not in scenario_measure_map:
                                scenario_measure_map[scenario.pk] = []
                            scenario_measure_map[scenario.pk].append(new_measure.pk)

                    except IntegrityError:
                        _log.error(
                            "Measure state_id, measure_id, application_sacle, and implementation_status already exists -- skipping for now")

                new_items.append(test_dict)

            # connect back up the scenario measures
            for scenario_id, measure_list in scenario_measure_map.items():

                # create a new scenario from the old one
                scenario = Scenario.objects.get(pk=scenario_id)

                scenario.pk = None
                scenario.property_state = merged_state
                scenario.save()  # save to get new id

                scenario.copy_initial_meters(scenario_id)

                # get the measures
                measures = PropertyMeasure.objects.filter(pk__in=measure_list)
                for measure in measures:
                    scenario.measures.add(measure)
                scenario.save()

        return merged_state


@receiver(pre_delete, sender=PropertyState)
def pre_delete_state(sender, **kwargs):
    # remove all the property measures. Not sure why the cascading delete
    # isn't working here.
    kwargs['instance'].propertymeasure_set.all().delete()


class PropertyView(models.Model):
    """
    Similar to the old world of canonical building.

    A PropertyView contains a reference to a property (which should not change) and to a
    cycle (time period), and a state (characteristics).

    """
    # different property views can be associated with each other (2012, 2013)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='views')
    cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT)
    state = models.ForeignKey(PropertyState, on_delete=models.CASCADE)

    labels = models.ManyToManyField(StatusLabel)

    # notes has a relationship here -- PropertyViews have notes, not the state, and not the property.

    def __str__(self):
        return 'Property View - %s' % self.pk

    class Meta:
        unique_together = ('property', 'cycle',)
        index_together = [['state', 'cycle']]

    def __init__(self, *args, **kwargs):
        self._import_filename = kwargs.pop('import_filename', None)
        super().__init__(*args, **kwargs)

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


@receiver(post_save, sender=PropertyView)
def post_save_property_view(sender, **kwargs):
    """
    When changing/saving the PropertyView, go ahead and touch the Property (if linked) so that the
    record receives an updated datetime
    """
    if kwargs['instance'].property:
        kwargs['instance'].property.save()


class PropertyAuditLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    parent1 = models.ForeignKey('PropertyAuditLog', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='propertyauditlog_parent1')
    parent2 = models.ForeignKey('PropertyAuditLog', on_delete=models.CASCADE, blank=True, null=True,
                                related_name='propertyauditlog_parent2')

    # store the parent states as well so that we can quickly return which state is associated
    # with the parents of the audit log without having to query the parent audit log to grab
    # the state
    parent_state1 = models.ForeignKey(PropertyState, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='parent_state1')
    parent_state2 = models.ForeignKey(PropertyState, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='parent_state2')

    state = models.ForeignKey('PropertyState', on_delete=models.CASCADE, related_name='propertyauditlog_state')
    view = models.ForeignKey('PropertyView', on_delete=models.CASCADE, related_name='propertyauditlog_view', null=True)

    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    import_filename = models.CharField(max_length=255, null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        index_together = [['state', 'name'], ['parent_state1', 'parent_state2']]


@receiver(pre_save, sender=PropertyState)
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


m2m_changed.connect(compare_orgs_between_label_and_target, sender=PropertyView.labels.through)
