# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import unicode_literals

import copy
import logging
import pdb
import re
from os import path

from django.apps import apps
from django.contrib.postgres.fields import JSONField
from django.db import IntegrityError
from django.db import models
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from quantityfield.fields import QuantityField

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
from seed.utils.time import convert_to_js_timestamp

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

    # Track when the entry was created and when it was updated
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'properties'

    def __unicode__(self):
        return u'Property - %s' % (self.pk)


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

    # A unique building identifier as defined by DOE's current effort (link to follow)
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

    generation_date = models.DateTimeField(null=True, blank=True)
    release_date = models.DateTimeField(null=True, blank=True)

    energy_score = models.IntegerField(null=True, blank=True)
    # Need to add another field eventually to define the source of the EUI's and other
    # reported fields. Ideally would have the ability to provide the same field from
    # multiple data sources. For example, site EUI (portfolio manager), site EUI (calculated),
    # site EUI (modeled 8/4/2017).
    site_eui = models.FloatField(null=True, blank=True)
    site_eui_weather_normalized = models.FloatField(null=True, blank=True)
    site_eui_modeled = models.FloatField(null=True, blank=True)
    source_eui = models.FloatField(null=True, blank=True)
    source_eui_weather_normalized = models.FloatField(null=True, blank=True)
    source_eui_modeled = models.FloatField(null=True, blank=True)

    energy_alerts = models.TextField(null=True, blank=True)
    space_alerts = models.TextField(null=True, blank=True)
    building_certification = models.CharField(max_length=255, null=True, blank=True)

    analysis_start_time = models.DateTimeField(null=True)
    analysis_end_time = models.DateTimeField(null=True)
    analysis_state = models.IntegerField(choices=ANALYSIS_STATE_TYPES,
                                         default=ANALYSIS_STATE_NOT_STARTED,
                                         null=True)
    analysis_state_message = models.TextField(null=True)

    # extra columns for pint interpretation base units in database will
    # continue to be imperial these will become the canonical columns in
    # future, with the old ones above to be culled once OGBS merges the metric
    # units work (scheduled for late 2017)

    # TODO: eventually need to add these fields to the coparent SQL query below.
    gross_floor_area_pint = QuantityField('ft**2', null=True, blank=True)
    conditioned_floor_area_pint = QuantityField('ft**2', null=True, blank=True)
    occupied_floor_area_pint = QuantityField('ft**2', null=True, blank=True)
    site_eui_pint = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    source_eui_weather_normalized_pint = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    site_eui_weather_normalized_pint = QuantityField('kBtu/ft**2/year', null=True, blank=True)
    source_eui_pint = QuantityField('kBtu/ft**2/year', null=True, blank=True)

    extra_data = JSONField(default=dict, blank=True)
    measures = models.ManyToManyField('Measure', through='PropertyMeasure')

    class Meta:
        index_together = [
            ['import_file', 'data_state'],
            ['import_file', 'data_state', 'merge_state'],
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

            if not self.organization:
                pdb.set_trace()

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
                        elif log.parent1.name == 'System Match' and log.parent1.parent1.name == 'Import Creation' and \
                                log.parent1.parent2.name == 'Import Creation':
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
        SimulationClass = apps.get_model('seed', 'Simulation')
        ScenarioClass = apps.get_model('seed', 'Scenario')
        PropertyMeasureClass = apps.get_model('seed', 'PropertyMeasure')

        # TODO: get some items off of this property view - labels and eventually notes

        # collect the relationships
        no_measure_scenarios = [x for x in state2.scenarios.filter(measures__isnull=True)] + \
                               [x for x in state1.scenarios.filter(measures__isnull=True)]
        building_files = [x for x in state2.building_files.all()] + [x for x in state1.building_files.all()]
        simulations = [x for x in SimulationClass.objects.filter(property_state__in=[state1, state2])]
        measures = [x for x in PropertyMeasureClass.objects.filter(property_state__in=[state1, state2])]

        # copy in the no measure scenarios
        for new_s in no_measure_scenarios:
            new_s.pk = None
            new_s.save()
            merged_state.scenarios.add(new_s)

        for new_bf in building_files:
            new_bf.pk = None
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
                        new_measure.pk = None
                        new_measure.property_state = merged_state
                        new_measure.save()

                        # grab the scenario that is attached to the orig measure and create a new connection
                        for scenario in measure.scenario_set.all():
                            if scenario.pk not in scenario_measure_map.keys():
                                scenario_measure_map[scenario.pk] = []
                            scenario_measure_map[scenario.pk].append(new_measure.pk)

                    except IntegrityError:
                        _log.error(
                            "Measure state_id, measure_id, application_sacle, and implementation_status already exists -- skipping for now")

                new_items.append(test_dict)

            # connect back up the scenario measures
            for scenario_id, measure_list in scenario_measure_map.items():
                # create a new scenario from the old one
                scenario = ScenarioClass.objects.get(pk=scenario_id)
                scenario.pk = None
                scenario.property_state = merged_state
                scenario.save()  # save to get new id

                # get the measures
                measures = PropertyMeasureClass.objects.filter(pk__in=measure_list)
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
    property = models.ForeignKey(Property, related_name='views', on_delete=models.CASCADE)
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


@receiver(post_save, sender=PropertyView)
def post_save_property_view(sender, **kwargs):
    """
    When changing/saving the PropertyView, go ahead and touch the Property (if linked) so that the record
    receives an updated datetime
    """
    if kwargs['instance'].property:
        kwargs['instance'].property.save()


class PropertyAuditLog(models.Model):
    organization = models.ForeignKey(Organization)
    parent1 = models.ForeignKey('PropertyAuditLog', blank=True, null=True,
                                related_name='propertyauditlog_parent1')
    parent2 = models.ForeignKey('PropertyAuditLog', blank=True, null=True,
                                related_name='propertyauditlog_parent2')

    # store the parent states as well so that we can quickly return which state is associated
    # with the parents of the audit log without having to query the parent audit log to grab
    # the state
    parent_state1 = models.ForeignKey(PropertyState, blank=True, null=True,
                                      related_name='parent_state1')
    parent_state2 = models.ForeignKey(PropertyState, blank=True, null=True,
                                      related_name='parent_state2')

    state = models.ForeignKey('PropertyState', related_name='propertyauditlog_state')
    view = models.ForeignKey('PropertyView', related_name='propertyauditlog_view', null=True)

    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    import_filename = models.CharField(max_length=255, null=True, blank=True)
    record_type = models.IntegerField(choices=DATA_UPDATE_TYPE, null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        index_together = [['state', 'name'], ['parent_state1', 'parent_state2']]
