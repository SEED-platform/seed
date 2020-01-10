# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
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

SEED_DATA_SOURCES = (
    (ASSESSED_RAW, 'Assessed Raw'),
    (ASSESSED_BS, 'Assessed'),
    (PORTFOLIO_RAW, 'Portfolio Raw'),
    (PORTFOLIO_BS, 'Portfolio'),
    (COMPOSITE_BS, 'BuildingSnapshot'),  # I don't think we need this, but I am leaving it for now.
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
        on_delete=models.CASCADE,
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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_('Project'), )

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
