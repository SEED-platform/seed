# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.models import (
    SEED_DATA_SOURCES,
)

# This is the inverse mapping of the property and tax lots that are prepended to the fields
# for the other table.
# INVENTORY_MAP_OPPOSITE_PREPEND = {
#     'property': 'tax',
#     'propertystate': 'tax',
#     'taxlot': 'property',
#     'taxlotstate': 'property',
# }
#
# COLUMN_OPPOSITE_TABLE = {
#     'PropertyState': 'TaxLotState',
#     'TaxLotState': 'PropertyState',
# }

INVENTORY_DISPLAY = {
    'PropertyState': 'Property',
    'TaxLotState': 'Tax Lot',
    'Property': 'Property',
    'TaxLot': 'Tax Lot',
}
_log = logging.getLogger(__name__)


def get_table_and_column_names(column_mapping, attr_name='column_raw'):
    """Turns the Column.column_names into a serializable list of str."""
    attr = getattr(column_mapping, attr_name, None)
    if not attr:
        return attr

    return [t for t in attr.all().values_list('table_name', 'column_name')]


def get_column_mapping(raw_column, organization, attr_name='column_mapped'):
    """Find the ColumnMapping objects that exist in the database from a raw_column

    :param raw_column: str, the column name of the raw data.
    :param organization: Organization inst.
    :param attr_name: str, name of attribute on ColumnMapping to pull out.
        whether we're looking at a mapping from the perspective of
        a raw_column (like we do when creating a mapping), or mapped_column,
        (like when we're applying that mapping).
    :returns: list of mapped items, float representation of confidence.

    """
    from seed.models.columns import Column

    if not isinstance(raw_column, list):
        column_raw = [raw_column]
    else:
        # NL 12/6/2016 - We should never get here, if we see this then find out why and remove the
        # list. Eventually delete this code.
        raise Exception("I am a LIST! Which makes no sense!")

    # Should only return one column
    cols = Column.objects.filter(
        organization=organization, column_name__in=column_raw
    )

    try:
        previous_mapping = ColumnMapping.objects.get(
            super_organization=organization,
            column_raw__in=cols,
        )
    except ColumnMapping.MultipleObjectsReturned:
        _log.debug("ColumnMapping.MultipleObjectsReturned in get_column_mapping")
        # handle the special edge-case where remove dupes does not get
        # called by ``get_or_create``
        ColumnMapping.objects.filter(super_organization=organization, column_raw__in=cols).delete()

        # Need to delete and then just allow for the system to re-attempt the match because
        # the old matches are no longer valid.
        return None
    except ColumnMapping.DoesNotExist:
        # Mapping column does not exist
        return None

    column_names = get_table_and_column_names(previous_mapping, attr_name=attr_name)

    # Check if the mapping is a one-to-one mapping, that is, there is only one mapping available.
    # As far as I know, this should always be the case because of the MultipleObjectsReturned
    # from above.
    if previous_mapping.is_direct():
        column_names = column_names[0]
    else:
        # NL 12/2/2016 - Adding this here for now as a catch. If we get here, then we have problems.
        raise Exception("The mapping returned with not direct!")

    return column_names[0], column_names[1], 100


class ColumnMapping(models.Model):
    """Stores previous user-defined column mapping.

    We'll pull from this when pulling from varied, dynamic
    source data to present the user with previous choices for that
    same field in subsequent data loads.

    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    source_type = models.IntegerField(choices=SEED_DATA_SOURCES, null=True, blank=True)
    super_organization = models.ForeignKey(SuperOrganization, on_delete=models.CASCADE, verbose_name=_('SeedOrg'),
                                           blank=True, null=True, related_name='column_mappings')
    column_raw = models.ManyToManyField('Column', related_name='raw_mappings', blank=True, )
    column_mapped = models.ManyToManyField('Column', related_name='mapped_mappings', blank=True, )

    # This field is the database column which allows checks for delimited values (e.g. a;b;c;d)
    DELIMITED_FIELD = ('TaxLotState', 'jurisdiction_tax_lot_id', 'Jurisdiction Tax Lot ID', False)

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
        return not self.is_direct()

    def remove_duplicates(self, qs, m2m_type='column_raw'):
        """
        Remove any other Column Mappings that use these columns.

        :param qs: queryset of ``Column``. These are the Columns in a M2M with
            this instance.
        :param m2m_type: str, the name of the field we're comparing against.
            Defaults to 'column_raw'.

        """
        ColumnMapping.objects.filter(
            **{
                '{0}__in'.format(m2m_type): qs,
                'super_organization': self.super_organization
            }
        ).exclude(pk=self.pk).delete()

    def save(self, *args, **kwargs):
        """
        Overrides default model save to eliminate duplicate mappings.

        .. warning ::
            Other column mappings which have the same raw_columns in them
            will be removed!

        """
        super().save(*args, **kwargs)
        # Because we need to have saved our ColumnMapping in order to have M2M,
        # We must create it before we prune older references.
        self.remove_duplicates(self.column_raw.all())

    def __str__(self):
        return '{0}: {1} - {2}'.format(
            self.pk, self.column_raw.all(), self.column_mapped.all()
        )

    @staticmethod
    def get_column_mappings(organization):
        """
        Returns dict of all the column mappings for an Organization's given
        source type

        Use this when actually performing mapping between data sources, but only
        call it after all of the mappings have been saved to the ``ColumnMapping``
        table.

        ..code:

            {
                'Wookiee': ('PropertyState', 'Dothraki', 'DisplayName', True),
                'Ewok': ('TaxLotState', 'Hattin', 'DisplayName', True),
                'eui': ('PropertyState', 'site_eui', 'DisplayName', True),
                'address': ('TaxLotState', 'address', 'DisplayName', True)
            }

        :param organization: instance, Organization.
        :returns: dict, list of dict.
        """
        column_mappings = ColumnMapping.objects.filter(super_organization=organization)
        mapping = {}
        for cm in column_mappings:
            # Iterate over the column_mappings. The column_mapping is a pointer to a raw column and a mapped column.
            # See the method documentation to understand the result.
            if not cm.column_mapped.all().exists():
                continue

            key = cm.column_raw.all().values_list('table_name', 'column_name', 'display_name',
                                                  'is_extra_data')
            value = cm.column_mapped.all().values_list('table_name', 'column_name', 'display_name',
                                                       'is_extra_data')

            if len(key) != 1:
                raise Exception("There is either none or more than one mapping raw column")

            if len(value) != 1:
                raise Exception("There is either none or more than one mapping dest column")

            key = key[0]
            value = value[0]

            # These should be lists of one element each.
            mapping[key[1]] = value

        # _log.debug("Mappings from get_column_mappings is: {}".format(mapping))
        return mapping, []

    @staticmethod
    def get_column_mappings_by_table_name(organization):
        """
        Breaks up the get_column_mappings into another layer to provide access by the table
        name as a key.

        :param organization: instance, Organization
        :return: dict
        """

        data, _ = ColumnMapping.get_column_mappings(organization)

        tables = set()
        for k, v in data.items():
            tables.add(v[0])

        # initialize the new container to store the results
        # (there has to be a better way of doing this... not enough time)
        container = {}
        for t in tables:
            container[t] = {}

        for k, v in data.items():
            container[v[0]][k] = v

        # Container will be in the format:
        #
        # container = {
        #     'PropertyState': {
        #         'Wookiee': ('PropertyState', 'Dothraki'),
        #         'eui': ('PropertyState', 'site_eui'),
        #     },
        #     'TaxLotState': {
        #         'address': ('TaxLotState', 'address'),
        #         'Ewok': ('TaxLotState', 'Hattin'),
        #     }
        # }
        return container

    @staticmethod
    def delete_mappings(organization):
        """
        Delete all the mappings for an organization. Note that this will erase all the mappings
        so if a user views an existing Data Mapping the mappings will not show up as the actual
        mapping, rather, it will show up as new suggested mappings

        :param organization: instance, Organization
        :return: int, Number of records that were deleted
        """
        count, _ = ColumnMapping.objects.filter(super_organization=organization).delete()
        return count
