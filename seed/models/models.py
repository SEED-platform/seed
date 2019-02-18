# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from collections import defaultdict

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django_extensions.db.models import TimeStampedModel

from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.projects import Project
from seed.utils.generic import obj_to_dict

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
    (COMPOSITE_BS, 'BuildingSnapshot'),  # I don't think we need this, but I am leaving it for now.
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
MERGE_STATE_DELETE = 4
MERGE_STATE = (
    (MERGE_STATE_UNKNOWN, 'Unknown'),
    (MERGE_STATE_NEW, 'New Record'),
    (MERGE_STATE_MERGED, 'Merged Record'),
    (MERGE_STATE_DUPLICATE, 'Duplicate Record'),
    (MERGE_STATE_DELETE, 'Delete Record'),  # typically set after unmerging two records
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

    name = models.CharField(_('name'), max_length=Project.PROJECT_NAME_MAX_LENGTH)
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
        'Residential',
        'Non-Residential',
        'Violation',
        'Compliant',
        'Missing Data',
        'Questionable Report',
        'Update Bldg Info',
        'Call',
        'Email',
        'High EUI',
        'Low EUI',
        'Exempted',
        'Extension',
        'Change of Ownership',
    ]

    class Meta:
        unique_together = ('name', 'super_organization')
        ordering = ['-name']

    def __str__(self):
        return '{0} - {1}'.format(self.name, self.color)

    def to_dict(self):
        return obj_to_dict(self)


class Compliance(TimeStampedModel):
    compliance_type = models.CharField(
        _('compliance_type'),
        max_length=30,
        choices=COMPLIANCE_CHOICES,
        default=BENCHMARK_COMPLIANCE_CHOICE
    )
    start_date = models.DateField(_('start_date'), null=True, blank=True)
    end_date = models.DateField(_('end_date'), null=True, blank=True)
    deadline_date = models.DateField(_('deadline_date'), null=True, blank=True)
    project = models.ForeignKey(Project, verbose_name=_('Project'), )

    def __str__(self):
        return 'Compliance %s for project %s' % (
            self.compliance_type, self.project
        )

    def to_dict(self):
        return obj_to_dict(self)


class Unit(models.Model):
    """Unit of measure for a Column Value."""
    STRING = 1
    DECIMAL = 2  # This is not used anymore, use float
    FLOAT = 3
    DATE = 4
    DATETIME = 5
    INTEGER = 6

    UNIT_TYPES = (
        (STRING, 'String'),
        (INTEGER, 'Integer'),
        (FLOAT, 'Float'),
        (DATE, 'Date'),
        (DATETIME, 'Datetime'),
    )

    unit_name = models.CharField(max_length=255)
    unit_type = models.IntegerField(choices=UNIT_TYPES, default=STRING)

    def __str__(self):
        return '{0} Format: {1}'.format(self.unit_name, self.unit_type)


class ThermalConversions():
    # Conversion factors taken from https://portfoliomanager.energystar.gov/pdf/reference/Thermal%20Conversions.pdf

    us_kbtu_conversion_factors = defaultdict(lambda: {})

    us_kbtu_conversion_factors["Electricity"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Electricity"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Electricity"]["kWh"] = 3.41200000000
    us_kbtu_conversion_factors["Electricity"]["MWh (million Watt-hours)"] = 3412.00000000000
    us_kbtu_conversion_factors["Electricity"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Natural Gas"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Natural Gas"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Natural Gas"]["cf"] = 1.02600000000
    us_kbtu_conversion_factors["Natural Gas"]["Ccf (hundred cubic feet)"] = 102.60000000000
    us_kbtu_conversion_factors["Natural Gas"]["Kcf (thousand cubic feet)"] = 1026.00000000000
    us_kbtu_conversion_factors["Natural Gas"]["Mcf (million cubic feet)"] = 1026000.00000000000
    us_kbtu_conversion_factors["Natural Gas"]["Therms"] = 100.00000000000
    us_kbtu_conversion_factors["Natural Gas"]["cubic meters"] = 36.30300000000
    us_kbtu_conversion_factors["Natural Gas"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Fuel Oil (No. 1)"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 1)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 1)"]["Gallons (US)"] = 139.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 1)"]["Gallons (UK)"] = 166.92700000000
    us_kbtu_conversion_factors["Fuel Oil (No. 1)"]["liters"] = 36.72000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 1)"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Fuel Oil (No. 2)"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 2)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 2)"]["Gallons (US)"] = 138.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 2)"]["Gallons (UK)"] = 165.72600000000
    us_kbtu_conversion_factors["Fuel Oil (No. 2)"]["liters"] = 36.45600000000
    us_kbtu_conversion_factors["Fuel Oil (No. 2)"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Fuel Oil (No. 4)"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 4)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 4)"]["Gallons (US)"] = 146.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 4)"]["Gallons (UK)"] = 175.33300000000
    us_kbtu_conversion_factors["Fuel Oil (No. 4)"]["liters"] = 38.56900000000
    us_kbtu_conversion_factors["Fuel Oil (No. 4)"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Fuel Oil (No. 5 & No. 6)"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 5 & No. 6)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 5 & No. 6)"]["Gallons (US)"] = 150.00000000000
    us_kbtu_conversion_factors["Fuel Oil (No. 5 & No. 6)"]["Gallons (UK)"] = 180.13700000000
    us_kbtu_conversion_factors["Fuel Oil (No. 5 & No. 6)"]["liters"] = 39.62600000000
    us_kbtu_conversion_factors["Fuel Oil (No. 5 & No. 6)"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Diesel"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Diesel"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Diesel"]["Gallons (US)"] = 138.00000000000
    us_kbtu_conversion_factors["Diesel"]["Gallons (UK)"] = 165.72600000000
    us_kbtu_conversion_factors["Diesel"]["liters"] = 36.45600000000
    us_kbtu_conversion_factors["Diesel"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Kerosene"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Kerosene"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Kerosene"]["Gallons (US)"] = 135.00000000000
    us_kbtu_conversion_factors["Kerosene"]["Gallons (UK)"] = 162.12300000000
    us_kbtu_conversion_factors["Kerosene"]["liters"] = 35.66300000000
    us_kbtu_conversion_factors["Kerosene"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Propane"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Propane"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Propane"]["cf"] = 2.51600000000
    us_kbtu_conversion_factors["Propane"]["Ccf (hundred cubic feet)"] = 251.60000000000
    us_kbtu_conversion_factors["Propane"]["Kcf (thousand cubic feet)"] = 2516.00000000000
    us_kbtu_conversion_factors["Propane"]["Gallons (US)"] = 92.00000000000
    us_kbtu_conversion_factors["Propane"]["Gallons (UK)"] = 110.48400000000
    us_kbtu_conversion_factors["Propane"]["liters"] = 24.30400000000
    us_kbtu_conversion_factors["Propane"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["District Steam"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["District Steam"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["District Steam"]["Lbs"] = 1.19400000000
    us_kbtu_conversion_factors["District Steam"]["kLbs (thousand pounds)"] = 1194.00000000000
    us_kbtu_conversion_factors["District Steam"]["MLbs (million pounds)"] = 1194000.00000000000
    us_kbtu_conversion_factors["District Steam"]["therms"] = 100.00000000000
    us_kbtu_conversion_factors["District Steam"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["District Steam"]["kg"] = 2.63200000000
    us_kbtu_conversion_factors["District Hot Water"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["District Hot Water"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["District Hot Water"]["Therms"] = 100.00000000000
    us_kbtu_conversion_factors["District Hot Water"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["District Chilled Water"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["District Chilled Water"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["District Chilled Water"]["Ton Hours"] = 12.00000000000
    us_kbtu_conversion_factors["District Chilled Water"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["Tons"] = 25090.00000000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["Lbs"] = 12.54500000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["kLbs (thousand pounds)"] = 12545.00000000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["MLbs (million pounds)"] = 12545000.00000000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["Tonnes (metric)"] = 27658.35500000000
    us_kbtu_conversion_factors["Coal (anthracite)"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["Tons"] = 24930.00000000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["Lbs"] = 12.46500000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["kLbs (thousand pounds)"] = 12465.00000000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["MLbs (million pounds)"] = 12465000.00000000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["Tonnes (metric)"] = 27482.00000000000
    us_kbtu_conversion_factors["Coal (bituminous)"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Coke"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Coke"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Coke"]["Tons"] = 24800.00000000000
    us_kbtu_conversion_factors["Coke"]["Lbs"] = 12.40000000000
    us_kbtu_conversion_factors["Coke"]["kLbs (thousand pounds)"] = 12400.00000000000
    us_kbtu_conversion_factors["Coke"]["MLbs (million pounds)"] = 12400000.00000000000
    us_kbtu_conversion_factors["Coke"]["Tonnes (metric)"] = 27339.00000000000
    us_kbtu_conversion_factors["Coke"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Wood"]["kBtu"] = 1.00000000000
    us_kbtu_conversion_factors["Wood"]["MBtu/MMBtu (million Btu)"] = 1000.00000000000
    us_kbtu_conversion_factors["Wood"]["Tons"] = 17480.00000000000
    us_kbtu_conversion_factors["Wood"]["Tonnes (metric)"] = 15857.00000000000
    us_kbtu_conversion_factors["Wood"]["GJ"] = 947.81700000000
    us_kbtu_conversion_factors["Other"]["kBtu"] = 1.00000000000

    # can_kbtu_conversion_factors = defaultdict(lambda: {})
