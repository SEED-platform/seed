# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from seed.landing.models import SEEDUser as User
from seed.lib.mappings.mapping_data import MappingData
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.models import (
    Enum,
    Unit,
    SEED_DATA_SOURCES,
)

import logging

_log = logging.getLogger(__name__)


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
            super_organization=organization, column_raw__in=cols,
        )
    except ColumnMapping.MultipleObjectsReturned:
        # # handle the special edge-case where remove dupes doesn't get
        # # called by ``get_or_create``
        ColumnMapping.objects.filter(
            super_organization=organization,
            column_raw__in=cols
        ).delete()

        previous_mapping, _ = ColumnMapping.objects.get_or_create(
            super_organization=organization,
            column_raw__in=cols
        )
    except ColumnMapping.DoesNotExist:
        return None

    column_names = _get_column_names(previous_mapping, attr_name=attr_name)

    if previous_mapping.is_direct():
        column_names = column_names[0]

    # TODO: return the correct table name!
    return 'PropertyState', column_names, 100


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
    table_name = models.CharField(max_length=512, blank=True, db_index=True, )
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

    @staticmethod
    def create_mappings(mappings, organization, user):
        """
        Create the mappings for an organization and a user based on a simple
        array of array object.

        .. note:

            Note that as of 09/15/2016 - extra data still needs to be defined in the mappings, it
            will no longer magically appear in the extra_data field if the user did not specify how
            to map it.

        Args:
            mappings: dictionary containing mapping information

                mappings: [
                    {
                        'from_field': 'eui',
                        'to_field': 'energy_use_intensity',
                        'to_table_name': 'property',
                    },
                    {
                        'from_field': 'eui',
                        'to_field': 'energy_use_intensity',
                        'to_table_name': 'property',
                    }
                ]

            organization: Organization object
            user: User object

        Returns:
            True (data are saved in the ColumnMapping table in the database)

        """

        # Take the existing object and return the same object with the db column objects added to
        # the dictionary (to_column_object and from_column_object)
        mappings = Column._column_fields_to_columns(mappings, organization)

        for mapping in mappings:
            if isinstance(mapping, dict):

                try:
                    column_mapping, _ = ColumnMapping.objects.get_or_create(
                        super_organization=organization,
                        column_raw__in=mapping['from_column_object'],
                    )
                except ColumnMapping.MultipleObjectsReturned:
                    # handle the special edge-case where remove dupes doesn't get
                    # called by ``get_or_create``
                    ColumnMapping.objects.filter(
                        super_organization=organization,
                        column_raw__in=mapping['from_column_object'],
                    ).delete()

                    column_mapping, _ = ColumnMapping.objects.get_or_create(
                        super_organization=organization,
                        column_raw__in=mapping['from_column_object'],
                    )

                # Clear out the column_raw and column mapped relationships. -- NL really? history?
                column_mapping.column_raw.clear()
                column_mapping.column_mapped.clear()

                # Add all that we got back from the interface back in the M2M rel.
                [column_mapping.column_raw.add(raw_col) for raw_col in
                 mapping['from_column_object']]
                if mapping['to_column_object'] is not None:
                    [column_mapping.column_mapped.add(dest_col) for dest_col in
                     mapping['to_column_object']]

                column_mapping.user = user
                column_mapping.save()
            else:
                raise TypeError("Mapping object needs to be of type dict")

        return True

    @staticmethod
    def _column_fields_to_columns(fields, organization):
        """
        List of dictionaries to process into column objects. This method will create the columns
        if they did not previously exist. Note that fields are probably mutable, but the method
        returns a new list of fields.

        .. example:

            test_map = [
                    {
                        'from_field': 'eui',
                        'to_field': 'site_eui',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'address',
                        'to_field': 'address',
                        'to_table_name': 'TaxLotState'
                    },
                    {
                        'from_field': 'Wookiee',
                        'to_field': 'Dothraki',
                        'to_table_name': 'PropertyState',
                    },
                ]

        Args:
            fields: list of dicts containing to and from fields
            organization: organization model instance

        Returns:
            dict with lists of columns to which is mappable.
        """

        def select_col_obj(column_name, table_name, organization_column):
            if organization_column:
                return [organization_column]
            else:
                # Try for "global" column definitions, e.g. BEDES. - Note the BEDES are not
                # loaded into the database as of 9/8/2016 so not sure if this code is ever
                # exercised
                obj = Column.objects.filter(organization=None, column_name=column_name).first()

                if obj:
                    # create organization mapped column
                    obj.pk = None
                    obj.id = None
                    obj.organization = organization
                    obj.save()

                    return [obj]
                else:
                    if table_name:
                        obj, _ = Column.objects.get_or_create(
                            organization=organization,
                            column_name=column_name,
                            table_name=table_name,
                            is_extra_data=is_extra_data,
                        )
                        return [obj]
                    else:
                        obj, _ = Column.objects.get_or_create(
                            organization=organization,
                            column_name=column_name,
                            is_extra_data=is_extra_data,
                        )
                        return [obj]

            return True

        md = MappingData()

        # Container to store the dicts with the Column object
        new_data = []

        for field in fields:
            new_field = field

            # find the mapping data column (i.e. the database fields) that match, if it exists
            # then set the extra data flag to true
            db_field = md.find_column(field['to_table_name'], field['to_field'])
            is_extra_data = False if db_field else True  # yes i am a db column, thus I am not extra_data

            # find the to_column
            to_org_col = Column.objects.filter(organization=organization,
                                               column_name=field['to_field'],
                                               table_name=field['to_table_name'],
                                               is_extra_data=is_extra_data).first()
            from_org_col = Column.objects.filter(organization=organization,
                                                 column_name=field['from_field'],
                                                 is_extra_data=is_extra_data).first()

            new_field['to_column_object'] = select_col_obj(
                field['to_field'],
                field['to_table_name'],
                to_org_col
            )
            new_field['from_column_object'] = select_col_obj(
                field['from_field'],
                "",
                from_org_col)

            new_data.append(new_field)

        return new_data

    @staticmethod
    def save_column_names(model_obj):
        """Save unique column names for extra_data in this organization.

        Basically this is a record of all the extra_data keys we've ever seen
        for a particular organization.

        :param model_obj: model_obj instance (either PropertyState or TaxLotState).
        """

        md = MappingData()

        for key in model_obj.extra_data:
            # Ascertain if our key is ``extra_data`` or not.

            # This is doing way to much work to find if the fields are extra data, especially
            # since that has been asked probably many times before.
            db_field = md.find_column(model_obj.__class__.__name__, key)
            is_extra_data = False if db_field else True  # yes i am a db column, thus I am not extra_data

            # get the name of the model object as a string to save into the database
            Column.objects.get_or_create(
                column_name=key[:511],
                is_extra_data=is_extra_data,
                organization=model_obj.organization,
                table_name=model_obj.__class__.__name__
            )

            # TODO: catch the MultipleObjectsReturns


class ColumnMapping(models.Model):
    """Stores previous user-defined column mapping.

    We'll pull from this when pulling from varied, dynamic
    source data to present the user with previous choices for that
    same field in subsequent data loads.

    """
    user = models.ForeignKey(User, blank=True, null=True)
    source_type = models.IntegerField(choices=SEED_DATA_SOURCES, null=True, blank=True)
    super_organization = models.ForeignKey(SuperOrganization, verbose_name=_('SeedOrg'),
                                           blank=True, null=True, related_name='column_mappings')
    column_raw = models.ManyToManyField('Column', related_name='raw_mappings', blank=True, )
    column_mapped = models.ManyToManyField('Column', related_name='mapped_mappings', blank=True, )

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
        super(ColumnMapping, self).save(*args, **kwargs)
        # Because we need to have saved our ColumnMapping in order to have M2M,
        # We must create it before we prune older references.
        self.remove_duplicates(self.column_raw.all())

    def __unicode__(self):
        return u'{0}: {1} - {2}'.format(
            self.pk, self.column_raw.all(), self.column_mapped.all()
        )

    @staticmethod
    def get_column_mappings(organization):
        """
        Returns dict of all the column mappings for an Organization's given
        source type

        :param organization: instance, Organization.
        :returns: dict, list of dict.

        Use this when actually performing mapping between data sources, but only
        call it after all of the mappings have been saved to the ``ColumnMapping``
        table.
        """
        from seed.utils.mapping import _get_table_and_column_names

        source_mappings = ColumnMapping.objects.filter(
            super_organization=organization
        )
        mapping = {}
        for item in source_mappings:
            if not item.column_mapped.all().exists():
                continue
            key = _get_table_and_column_names(item, attr_name='column_raw')[0]
            value = _get_table_and_column_names(item, attr_name='column_mapped')[0]

            # Concat is not used as of 2016-09-14: commenting out.
            # if isinstance(key, list) and len(key) > 1:
            #     concat_confs.append({
            #         'concat_columns': key,
            #         'target': value,
            #         'delimiter': ' '
            #     })
            #     continue

            # These should be lists of one element each.
            mapping[key[1]] = value

        _log.debug("Mappings from get_column_mappings is: {}".format(mapping))
        return mapping, []
