# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.models import (
    Enum,
    Unit,
    SEED_DATA_SOURCES,

)


def get_column_mapping(column_raw, organization, attr_name='column_mapped'):
    """Callable provided to MCM to return a previously mapped field.

    :param column_raw: str, the column name of the raw data.
    :param organization: Organization inst.
    :param attr_name: str, name of attribute on ColumnMapping to pull out.
        whether we're looking at a mapping from the perspective of
        a raw_column (like we do when creating a mapping), or mapped_column,
        (like when we're applying that mapping).
    :returns: list of mapped items, float representation of confidence.

    """
    from seed.utils.mapping import _get_column_names

    if not isinstance(column_raw, list):
        column_raw = [column_raw]

    cols = Column.objects.filter(
        organization=organization, column_name__in=column_raw
    )

    try:
        previous_mapping = ColumnMapping.objects.get(
            super_organization=organization,
            column_raw__in=cols,
        )

    except ColumnMapping.DoesNotExist:
        return None

    column_names = _get_column_names(previous_mapping, attr_name=attr_name)

    if previous_mapping.is_direct():
        column_names = column_names[0]

    return 'property', column_names, 100


def get_column_mappings(organization):
    """Returns dict of all the column mappings for an Organization's given source type

    :param organization: inst, Organization.
    :returns: dict, list of dict.

    Use this when actually performing mapping between data sources, but only call it after all of the mappings
    have been saved to the ``ColumnMapping`` table.

    """
    from seed.utils.mapping import _get_column_names

    source_mappings = ColumnMapping.objects.filter(
        super_organization=organization
    )
    concat_confs = []
    mapping = {}
    for item in source_mappings:
        if not item.column_mapped.all().exists():
            continue
        key = _get_column_names(item)
        value = _get_column_names(item, attr_name='column_mapped')[0]

        if isinstance(key, list) and len(key) > 1:
            concat_confs.append({
                'concat_columns': key,
                'target': value,
                'delimiter': ' '
            })
            continue

        # These should be lists of one element each.
        mapping[key[0]] = value

    return mapping, concat_confs


# TODO: Make this a static method on Column
def save_column_names(property_state, mapping=None):
    """Save unique column names for extra_data in this organization.

    Basically this is a record of all the extra_data keys we've ever seen
    for a particular organization.

    :param property_state: PropertyState instance.
    """
    from seed.utils import mapping as mapping_utils

    for key in property_state.extra_data:
        # Ascertain if our key is ``extra_data`` or not.
        is_extra_data = key not in mapping_utils.get_mappable_columns()
        Column.objects.get_or_create(
            organization=property_state.super_organization,
            column_name=key[:511],
            is_extra_data=is_extra_data
        )


class Column(models.Model):
    """The name of a column for a given organization."""
    SOURCE_PROPERTY = 'P'
    SOURCE_TAXLOT = 'T'
    SOURCE_CHOICES = (
        (SOURCE_PROPERTY, 'Property'),
        (SOURCE_TAXLOT, 'Taxlot'),
    )
    SOURCE_CHOICES_MAP = {
        SOURCE_PROPERTY: 'property',
        SOURCE_TAXLOT: 'taxlot',
    }

    organization = models.ForeignKey(SuperOrganization, blank=True, null=True)
    column_name = models.CharField(max_length=512, db_index=True)

    # name of the table which the column name applies, if the column name
    # is a db field
    table_name = models.CharField(max_length=512, blank=True, db_index=True,)
    unit = models.ForeignKey(Unit, blank=True, null=True)
    enum = models.ForeignKey(Enum, blank=True, null=True)
    is_extra_data = models.BooleanField(default=False)
    extra_data_source = models.CharField(
        max_length=1, null=True, blank=True,
        db_index=True, choices=SOURCE_CHOICES
    )

    class Meta:
        unique_together = (
            'organization', 'column_name', 'is_extra_data', 'extra_data_source')

    def __unicode__(self):
        return u'{0}'.format(self.column_name)


class ColumnMapping(models.Model):
    """Stores previous user-defined column mapping.

    We'll pull from this when pulling from varied, dynamic
    source data to present the user with previous choices for that
    same field in subsequent data loads.

    """
    user = models.ForeignKey(User, blank=True, null=True)
    source_type = models.IntegerField(
        choices=SEED_DATA_SOURCES, null=True, blank=True
    )
    super_organization = models.ForeignKey(
        SuperOrganization,
        verbose_name=_('SeedOrg'),
        blank=True,
        null=True,
        related_name='column_mappings'
    )
    column_raw = models.ManyToManyField(
        'Column',
        related_name='raw_mappings',
        blank=True,
    )
    column_mapped = models.ManyToManyField(
        'Column',
        related_name='mapped_mappings',
        blank=True,
    )

    def is_direct(self):
        """
        Returns True if the ColumnMapping is a direct mapping from imported
        column name to either a BEDES column or a previously imported column.
        Returns False if the ColumnMapping represents a concatenation.
        """
        return (
            (self.column_raw.count() == 1) and
            (self.column_mapped.count() == 1)
        )

    def is_concatenated(self):
        """
        Returns True if the ColumnMapping represents the concatenation of
        imported column names; else returns False.
        """
        return (not self.is_direct())

    def remove_duplicates(self, qs, m2m_type='column_raw'):
        """Remove any other Column Mappings that use these columns.

        :param qs: queryset of ``Column``. These are the Columns in a M2M with
            this instance.
        :param m2m_type: str, the name of the field we're comparing against.
            Defaults to 'column_raw'.

        """
        ColumnMapping.objects.filter(**{
            '{0}__in'.format(m2m_type): qs,
            'super_organization': self.super_organization
        }).exclude(pk=self.pk).delete()

    def save(self, *args, **kwargs):
        """Overrides default model save to eliminate duplicate mappings.

        .. warning ::
            Other column mappings which have the same raw_columns in them
            will be removed!

        """
        super(ColumnMapping, self).save(*args, **kwargs)
        # Because we need to have saved our ColumnMapping in order to have M2M,
        # We must create it before we prune older references.
        self.remove_duplicates(self.column_raw.all())

    def __unicode__(self):
        return u'{0}: {1} - {2}'.format(
            self.pk, self.column_raw.all(), self.column_mapped.all()
        )
