# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel
from django_pgjson.fields import JsonField

from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.managers.json import JsonManager
from seed.models.projects import (
    Project, ProjectBuilding, PROJECT_NAME_MAX_LENGTH
)
from seed.utils.generic import obj_to_dict


# Represents the data source of a given BuildingSnapshot

ASSESSED_RAW = 0
PORTFOLIO_RAW = 1
ASSESSED_BS = 2
PORTFOLIO_BS = 3
COMPOSITE_BS = 4
GREEN_BUTTON_RAW = 5
GREEN_BUTTON_BS = 6

SEED_DATA_SOURCES = (
    (ASSESSED_RAW, 'Assessed Raw'),
    (ASSESSED_BS, 'Assessed'),
    (PORTFOLIO_RAW, 'Portfolio Raw'),
    (PORTFOLIO_BS, 'Portfolio'),
    (COMPOSITE_BS, 'BuildingSnapshot'),
    (GREEN_BUTTON_RAW, 'Green Button Raw'),
)

# State of the data that was imported. This will be used to flag which
# rows are orphaned and can be deleted. TODO: There are a bunch of these states already
# defined in the data_importer/models.py file. Should probably revert this and use those.
DATA_STATE_UNKNOWN = 0
DATA_STATE_IMPORT = 1
DATA_STATE_MAPPING = 2
DATA_STATE_MATCHING = 3
DATA_STATE_DELETE = 4
DATA_STATE = (
    (DATA_STATE_UNKNOWN, 'Unknown'),
    (DATA_STATE_IMPORT, 'Post Import'),
    (DATA_STATE_MAPPING, 'Post Mapping'),
    (DATA_STATE_MATCHING, 'Post Matching'),
    (DATA_STATE_DELETE, 'Flagged for Deletion'),
)

# State of the merging for PropertyStates and TaxLotStates
MERGE_STATE_UNKNOWN = 0
MERGE_STATE_NEW = 1
MERGE_STATE_MERGED = 2
MERGE_STATE_DUPLICATE = 3
MERGE_STATE = (
    (MERGE_STATE_UNKNOWN, 'Unknown'),
    (MERGE_STATE_NEW, 'Orphaned as result of merge'),
    (MERGE_STATE_MERGED, 'Merged Record'),
    (MERGE_STATE_DUPLICATE, 'Duplicate Record'),
)

SEARCH_CONFIDENCE_RANGES = {
    'low': 0.4,
    'medium': 0.75,
    'high': 1.0,
}

NATURAL_GAS = 1
ELECTRICITY = 2
FUEL_OIL = 3
FUEL_OIL_NO_1 = 4
FUEL_OIL_NO_2 = 5
FUEL_OIL_NO_4 = 6
FUEL_OIL_NO_5_AND_NO_6 = 7
DISTRICT_STEAM = 8
DISTRICT_HOT_WATER = 9
DISTRICT_CHILLED_WATER = 10
PROPANE = 11
LIQUID_PROPANE = 12
KEROSENE = 13
DIESEL = 14
COAL = 15
COAL_ANTHRACITE = 16
COAL_BITUMINOUS = 17
COKE = 18
WOOD = 19
OTHER = 20
WATER = 21

ENERGY_TYPES = (
    (NATURAL_GAS, 'Natural Gas'),
    (ELECTRICITY, 'Electricity'),
    (FUEL_OIL, 'Fuel Oil'),
    (FUEL_OIL_NO_1, 'Fuel Oil No. 1'),
    (FUEL_OIL_NO_2, 'Fuel Oil No. 2'),
    (FUEL_OIL_NO_4, 'Fuel Oil No. 4'),
    (FUEL_OIL_NO_5_AND_NO_6, 'Fuel Oil No. 5 and No. 6'),
    (DISTRICT_STEAM, 'District Steam'),
    (DISTRICT_HOT_WATER, 'District Hot Water'),
    (DISTRICT_CHILLED_WATER, 'District Chilled Water'),
    (PROPANE, 'Propane'),
    (LIQUID_PROPANE, 'Liquid Propane'),
    (KEROSENE, 'Kerosene'),
    (DIESEL, 'Diesel'),
    (COAL, 'Coal'),
    (COAL_ANTHRACITE, 'Coal Anthracite'),
    (COAL_BITUMINOUS, 'Coal Bituminous'),
    (COKE, 'Coke'),
    (WOOD, 'Wood'),
    (OTHER, 'Other'),
)

KILOWATT_HOURS = 1
THERMS = 2
WATT_HOURS = 3

ENERGY_UNITS = (
    (KILOWATT_HOURS, 'kWh'),
    (THERMS, 'Therms'),
    (WATT_HOURS, 'Wh'),
)

# Used by compliance model but imported elsewhere
BENCHMARK_COMPLIANCE_CHOICE = 'Benchmarking'
AUDITING_COMPLIANCE_CHOICE = 'Auditing'
RETRO_COMMISSIONING_COMPLIANCE_CHOICE = 'Retro Commissioning'
COMPLIANCE_CHOICES = (
    (BENCHMARK_COMPLIANCE_CHOICE, _('Benchmarking')),
    (AUDITING_COMPLIANCE_CHOICE, _('Auditing')),
    (RETRO_COMMISSIONING_COMPLIANCE_CHOICE, _('Retro Commissioning')),
)

#
# Used in ``tasks.match_buildings``
#


# TO REMOVE
def get_ancestors(building):
    """gets all the non-raw, non-composite ancestors of a building

    Recursive function to traverse the tree upward.

    :param building: BuildingSnapshot inst.
    :returns: list of BuildingSnapshot inst., ancestors of building

    .. code-block:: python

           source_type {
               2: ASSESSED_BS,
               3: PORTFOLIO_BS,
               4: COMPOSITE_BS,
               6: GREEN_BUTTON_BS
           }
    """
    ancestors = []
    parents = building.parents.filter(source_type__in=[2, 3, 4, 6])
    ancestors.extend(parents.filter(source_type__in=[2, 3, 6]))
    for p in parents:
        ancestors.extend(get_ancestors(p))
    return ancestors


def get_sourced_attributes(snapshot):
    """Return all the attribute names that get sourced."""
    single_sources = []
    plural_sources = []
    for item in snapshot._meta.fields:
        if hasattr(snapshot, '{0}_source'.format(item.name)):
            single_sources.append(item.name)
        if hasattr(snapshot, '{0}_sources'.format(item.name)):
            plural_sources.append(item.name)

    return single_sources, plural_sources


def set_initial_sources(snapshot):
    """Sets the PK for the original sources to self."""

    # TODO: This has been removed in the new data model -- remove here??
    single, plural = get_sourced_attributes(snapshot)
    for attr in single:
        # We set the attribute source to be itself.
        setattr(snapshot, '{0}_source'.format(attr), snapshot)

    for attr in plural:
        # We have to assume that it's a dict
        attrs = getattr(snapshot, attr, {})
        sources = getattr(snapshot, '{0}_sources', {})
        for k in attrs:
            sources[k] = snapshot.pk

        setattr(snapshot, '{0}_sources'.format(attr), sources)

    return snapshot


# def _get_filtered_values(updated_values):
#     """Breaks out mappable, meta and source BuildingSnapshot attributes."""
#     from seed.utils.constants import META_FIELDS, EXCLUDE_FIELDS

#     mappable_values = {}
#     meta_values = {}
#     source_values = {}

#     for item in updated_values:
#         value = updated_values[item]
#         if item.endswith('_source'):
#             source_values[item] = value
#         elif item in META_FIELDS:
#             meta_values[item] = value
#         elif item not in EXCLUDE_FIELDS:
#             mappable_values[item] = value

#     return mappable_values, meta_values, source_values


# def _get_diff_sources(mappable, old_snapshot):
#     """Return a list of str for values that changed from old_snapshot."""
#     results = []
#     for item in mappable:
#         value = mappable[item]
#         if getattr(old_snapshot, item, None) != value and value:
#             results.append(item)

#     return results


# def update_building(old_snapshot, updated_values, user, *args, **kwargs):
#     """Creates a new snapshot with updated values."""
#     from seed.mappings import seed_mappings, mapper as seed_mapper

#     mappable, meta, sources = _get_filtered_values(updated_values)

#     # extra data will get filtered
#     extra_data = updated_values['extra_data']
#     extra_data = extra_data or old_snapshot.extra_data or {}

#     canon = old_snapshot.canonical_building or None
#     # Need to hydrate sources
#     sources = {
#         k: BuildingSnapshot.objects.get(pk=v) for k, v in sources.items() if v
#     }

#     # Handle the mapping of "normal" attributes.
#     new_snapshot = mapper.map_row(
#         mappable,
#         dict(seed_mappings.BuildingSnapshot_to_BuildingSnapshot),
#         BuildingSnapshot,
#         initial_data=sources  # Copy parent's source attributes.
#     )

#     # convert dates to something django likes
#     new_snapshot.clean()
#     new_snapshot.save()

#     diff_sources = _get_diff_sources(mappable, old_snapshot)
#     for diff in diff_sources:
#         setattr(new_snapshot, '{0}_source'.format(diff), new_snapshot)

#     new_snapshot.canonical_building = canon
#     new_snapshot.save()

#     # All all the orgs the old snapshot had.
#     new_snapshot.super_organization = old_snapshot.super_organization
#     # Move the meta data over.
#     for meta_val in meta:
#         setattr(new_snapshot, meta_val, meta[meta_val])
#     # Insert new_snapshot into the inheritance chain
#     old_snapshot.children.add(new_snapshot)
#     new_snapshot.import_file_id = old_snapshot.import_file_id

#     new_snapshot.extra_data = extra_data

#     # Update/override anything in extra data.
#     extra, sources = seed_mapper.merge_extra_data(
#         new_snapshot, old_snapshot, default=new_snapshot
#     )
#     new_snapshot.extra_data = extra
#     new_snapshot.extra_data_sources = sources
#     new_snapshot.save()

#     # If we had a canonical building and its can_snapshot was old, update.
#     if canon and canon.canonical_snapshot == old_snapshot:
#         canon.canonical_snapshot = new_snapshot
#         canon.save()

#     # If the old snapshot was in any project the ProjectBuilding set
#     # needs to be updated to point to the new snapshot. We might want
#     # to refactor ProjectBuildings to contain a CanonicalBuilding
#     # foreign key in the future.
#     old_snapshot.project_building_snapshots.all().update(
#         building_snapshot=new_snapshot
#     )

#     # Check to see if there are any new ``extra_data`` fields added for this
#     # org.
#     Column.save_column_names(new_snapshot)

#     return new_snapshot


class StatusLabel(TimeStampedModel):
    RED_CHOICE = 'red'
    ORANGE_CHOICE = 'orange'
    WHITE_CHOICE = 'white'
    BLUE_CHOICE = 'blue'
    LIGHT_BLUE_CHOICE = 'light blue'
    GREEN_CHOICE = 'green'
    GRAY_CHOICE = 'gray'

    COLOR_CHOICES = (
        (RED_CHOICE, _('red')),
        (BLUE_CHOICE, _('blue')),
        (LIGHT_BLUE_CHOICE, _('light blue')),
        (GREEN_CHOICE, _('green')),
        (WHITE_CHOICE, _('white')),
        (ORANGE_CHOICE, _('orange')),
        (GRAY_CHOICE, _('gray')),
    )

    name = models.CharField(_('name'), max_length=PROJECT_NAME_MAX_LENGTH)
    color = models.CharField(
        _('compliance_type'),
        max_length=30,
        choices=COLOR_CHOICES,
        default=GREEN_CHOICE
    )
    super_organization = models.ForeignKey(
        SuperOrganization,
        verbose_name=_('SeedOrg'),
        blank=True,
        null=True,
        related_name='labels'
    )

    DEFAULT_LABELS = [
        "Residential",
        "Non-Residential",
        "Violation",
        "Compliant",
        "Missing Data",
        "Questionable Report",
        "Update Bldg Info",
        "Call",
        "Email",
        "High EUI",
        "Low EUI",
        "Exempted",
        "Extension",
        "Change of Ownership",
    ]

    class Meta:
        unique_together = ('name', 'super_organization')
        ordering = ['-name']

    def __unicode__(self):
        return u"{0} - {1}".format(self.name, self.color)

    def to_dict(self):
        return obj_to_dict(self)


class Compliance(TimeStampedModel):

    compliance_type = models.CharField(
        _('compliance_type'),
        max_length=30,
        choices=COMPLIANCE_CHOICES,
        default=BENCHMARK_COMPLIANCE_CHOICE
    )
    start_date = models.DateField(_("start_date"), null=True, blank=True)
    end_date = models.DateField(_("end_date"), null=True, blank=True)
    deadline_date = models.DateField(_("deadline_date"), null=True, blank=True)
    project = models.ForeignKey(Project, verbose_name=_('Project'), )

    def __unicode__(self):
        return u"Compliance %s for project %s" % (
            self.compliance_type, self.project
        )

    def to_dict(self):
        return obj_to_dict(self)


class CustomBuildingHeaders(models.Model):
    """Specify custom building header mapping for display."""
    super_organization = models.ForeignKey(
        SuperOrganization,
        blank=True,
        null=True,
        verbose_name=_('SeedOrg'),
        related_name='custom_headers'
    )

    # 'existing, normalized name' -> 'preferred display name'
    # e.g. {'district': 'Boro'}
    building_headers = JsonField(default={})

    objects = JsonManager()


STRING = 1
DECIMAL = 2
FLOAT = 3
DATE = 4
DATETIME = 5

UNIT_TYPES = (
    (STRING, 'String'),
    (DECIMAL, 'Decimal'),
    (FLOAT, 'Float'),
    (DATE, 'Date'),
    (DATETIME, 'Datetime'),
)


class Unit(models.Model):
    """Unit of measure for a Column Value."""
    unit_name = models.CharField(max_length=255)
    unit_type = models.IntegerField(choices=UNIT_TYPES, default=STRING)

    def __unicode__(self):
        return u'{0} Format: {1}'.format(self.unit_name, self.unit_type)


class EnumValue(models.Model):
    """Individual Enumerated Type values."""
    value_name = models.CharField(max_length=255)

    def __unicode__(self):
        return u'{0}'.format(self.value_name)


class Enum(models.Model):
    """Defines a set of enumerated types for a column."""
    enum_name = models.CharField(max_length=255, db_index=True)
    enum_values = models.ManyToManyField(
        EnumValue, blank=True, related_name='values'
    )

    def __unicode__(self):
        """Just grab the first couple and the last enum_values to display."""
        enums = list(self.enum_values.all()[0:3])
        enums_string = ', '.join(enums)
        if self.enum_values.count() > len(enums):
            enums_string.append(' ... {0}'.format(self.enum_values.last()))

        return u'Enum: {0}: Values {1}'.format(
            self.enum_name, enums_string
        )


class NonCanonicalProjectBuildings(models.Model):
    """Holds a reference to all project buildings that do not point at a
    canonical building snapshot."""
    projectbuilding = models.ForeignKey(ProjectBuilding, primary_key=True)


class AttributeOption(models.Model):
    """Holds a single conflicting value for a BuildingSnapshot attribute."""
    value = models.TextField()
    value_source = models.IntegerField(choices=SEED_DATA_SOURCES)
    building_variant = models.ForeignKey(
        'BuildingAttributeVariant',
        null=True,
        blank=True,
        related_name='options'
    )


class BuildingAttributeVariant(models.Model):
    """Place to keep the options of BuildingSnapshot attribute variants.

    When we want to select which source's values should sit in the Canonical
    Building's position, we need to draw from a set of options determined
    during the matching phase. We should only have one 'Variant' container
    per field_name, per snapshot.

    """
    field_name = models.CharField(max_length=255)
    building_snapshot = models.ForeignKey(
        'BuildingSnapshot', related_name='variants', null=True, blank=True
    )

    class Meta:
        unique_together = ('field_name', 'building_snapshot')


class Meter(models.Model):
    """Meter specific attributes."""
    name = models.CharField(max_length=100)
    building_snapshot = models.ManyToManyField(
        'BuildingSnapshot', related_name='meters', blank=True
    )
    energy_type = models.IntegerField(choices=ENERGY_TYPES)
    energy_units = models.IntegerField(choices=ENERGY_UNITS)


class TimeSeries(models.Model):
    """For storing energy use over time."""
    begin_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    reading = models.FloatField(null=True)
    cost = models.DecimalField(max_digits=11, decimal_places=4, null=True)
    meter = models.ForeignKey(
        Meter, related_name='timeseries_data', null=True, blank=True
    )
