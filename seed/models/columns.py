# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import csv
import logging
import os.path
from collections import OrderedDict

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import pre_save
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.models import (
    Enum,
    Unit,
    SEED_DATA_SOURCES,
)
from seed.utils.strings import titlecase

# This is the inverse mapping of the property and tax lots that are prepended to the fields
# for the other table.
INVENTORY_MAP_OPPOSITE_PREPEND = {
    'property': 'tax',
    'propertystate': 'tax',
    'taxlot': 'property',
    'taxlotstate': 'property',
}

COLUMN_OPPOSITE_TABLE = {
    'PropertyState': 'TaxLotState',
    'TaxLotState': 'PropertyState',
}

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


class Column(models.Model):
    """The name of a column for a given organization."""

    # We have two concepts of the SOURCE. The table_name, which is mostly used, and the
    # SOURCE_* fields. Need to converge on one or the other.
    # SOURCE_PROPERTY = 'P'
    # SOURCE_TAXLOT = 'T'
    # SOURCE_CHOICES = (
    #     (SOURCE_PROPERTY, 'Property'),
    #     (SOURCE_TAXLOT, 'Taxlot'),
    # )
    # SOURCE_CHOICES_MAP = {
    #     SOURCE_PROPERTY: 'property',
    #     SOURCE_TAXLOT: 'taxlot',
    # }

    SHARED_NONE = 0
    SHARED_PUBLIC = 1

    SHARED_FIELD_TYPES = (
        (SHARED_NONE, 'None'),
        (SHARED_PUBLIC, 'Public')
    )

    PINNED_COLUMNS = [
        ('PropertyState', 'pm_property_id'),
        ('TaxLotState', 'jurisdiction_tax_lot_id')
    ]

    # These are the columns that are removed when looking to see if the records are the same
    COLUMN_EXCLUDE_FIELDS = [
        'id',
        'source_type',
        'data_state',
        'import_file',
        'merge_state',
        'confidence',
        'extra_data',
        # Records below are old and should not be uesed
        'source_eui_modeled_orig',
        'site_eui_orig',
        'occupied_floor_area_orig',
        'site_eui_weather_normalized_orig',
        'site_eui_modeled_orig',
        'source_eui_orig',
        'gross_floor_area_orig',
        'conditioned_floor_area_orig',
        'source_eui_weather_normalized_orig',
    ]

    # These are fields that should not be mapped to
    EXCLUDED_MAPPING_FIELDS = [
        'extra_data',
        'lot_number',
        'normalized_address',
    ]

    INTERNAL_TYPE_TO_DATA_TYPE = {
        'FloatField': 'double',  # yes, technically this is not the same, move along.
        'IntegerField': 'integer',
        'CharField': 'string',
        'TextField': 'string',
        'DateField': 'date',
        'DateTimeField': 'datetime',
        'BooleanField': 'boolean',
        'JSONField': 'string',
    }

    # These are the default columns ( also known as the fields in the database)
    DATABASE_COLUMNS = [
        {
            'column_name': 'pm_property_id',
            'table_name': 'PropertyState',
            'display_name': 'PM Property ID',
            'data_type': 'string',
        }, {
            'column_name': 'pm_parent_property_id',
            'table_name': 'PropertyState',
            'display_name': 'PM Parent Property ID',
            'data_type': 'string',
        }, {
            'column_name': 'jurisdiction_tax_lot_id',
            'table_name': 'TaxLotState',
            'display_name': 'Jurisdiction Tax Lot ID',
            'data_type': 'string',
        }, {
            'column_name': 'jurisdiction_property_id',
            'table_name': 'PropertyState',
            'display_name': 'Jurisdiction Property ID',
            'data_type': 'string',
        }, {
            'column_name': 'ubid',
            'table_name': 'PropertyState',
            'display_name': 'UBID',
            'data_type': 'string',
        }, {
            'column_name': 'custom_id_1',
            'table_name': 'PropertyState',
            'display_name': 'Custom ID 1',
            'data_type': 'string',
        }, {
            'column_name': 'custom_id_1',
            'table_name': 'TaxLotState',
            'display_name': 'Custom ID 1',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_1',
            'table_name': 'PropertyState',
            'display_name': 'Address Line 1',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_1',
            'table_name': 'TaxLotState',
            'display_name': 'Address Line 1',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_2',
            'table_name': 'PropertyState',
            'display_name': 'Address Line 2',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_2',
            'table_name': 'TaxLotState',
            'display_name': 'Address Line 2',
            'data_type': 'string',
        }, {
            'column_name': 'city',
            'table_name': 'PropertyState',
            'display_name': 'City',
            'data_type': 'string',
        }, {
            'column_name': 'city',
            'table_name': 'TaxLotState',
            'display_name': 'City',
            'data_type': 'string',
        }, {
            'column_name': 'state',
            'table_name': 'PropertyState',
            'display_name': 'State',
            'data_type': 'string',
        }, {
            'column_name': 'state',
            'table_name': 'TaxLotState',
            'display_name': 'State',
            'data_type': 'string',
        }, {
            # This should never be mapped to!
            'column_name': 'normalized_address',
            'table_name': 'PropertyState',
            'display_name': 'Normalized Address',
            'data_type': 'string',
        }, {
            # This should never be mapped to!
            'column_name': 'normalized_address',
            'table_name': 'TaxLotState',
            'display_name': 'Normalized Address',
            'data_type': 'string',
        }, {
            'column_name': 'postal_code',
            'table_name': 'PropertyState',
            'display_name': 'Postal Code',
            'data_type': 'string',
        }, {
            'column_name': 'postal_code',
            'table_name': 'TaxLotState',
            'display_name': 'Postal Code',
            'data_type': 'string',
        }, {
            # This field should never be mapped to!
            'column_name': 'lot_number',
            'table_name': 'PropertyState',
            'display_name': 'Associated Tax Lot ID',
            'data_type': 'string',
        }, {
            'column_name': 'property_name',
            'table_name': 'PropertyState',
            'display_name': 'Property Name',
            'data_type': 'string',
        }, {
            'column_name': 'latitude',
            'table_name': 'PropertyState',
            'display_name': 'Latitude',
            'data_type': 'number',
        }, {
            'column_name': 'longitude',
            'table_name': 'PropertyState',
            'display_name': 'Longitude',
            'data_type': 'number',
        }, {
            'column_name': 'campus',
            'table_name': 'Property',
            'display_name': 'Campus',
            'data_type': 'boolean',
            # 'type': 'boolean',
        }, {
            'column_name': 'updated',
            'table_name': 'Property',
            'display_name': 'Updated',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'created',
            'table_name': 'Property',
            'display_name': 'Created',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'updated',
            'table_name': 'TaxLot',
            'display_name': 'Updated',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'created',
            'table_name': 'TaxLot',
            'display_name': 'Created',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'gross_floor_area',
            'table_name': 'PropertyState',
            'display_name': 'Gross Floor Area',
            'data_type': 'area',
            # 'type': 'number',
        }, {
            'column_name': 'use_description',
            'table_name': 'PropertyState',
            'display_name': 'Use Description',
            'data_type': 'string',
        }, {
            'column_name': 'energy_score',
            'table_name': 'PropertyState',
            'display_name': 'ENERGY STAR Score',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'property_notes',
            'table_name': 'PropertyState',
            'display_name': 'Property Notes',
            'data_type': 'string',
        }, {
            'column_name': 'property_type',
            'table_name': 'PropertyState',
            'display_name': 'Property Type',
            'data_type': 'string',
        }, {
            'column_name': 'year_ending',
            'table_name': 'PropertyState',
            'display_name': 'Year Ending',
            'data_type': 'date',
        }, {
            'column_name': 'owner',
            'table_name': 'PropertyState',
            'display_name': 'Owner',
            'data_type': 'string',
        }, {
            'column_name': 'owner_email',
            'table_name': 'PropertyState',
            'display_name': 'Owner Email',
            'data_type': 'string',
        }, {
            'column_name': 'owner_telephone',
            'table_name': 'PropertyState',
            'display_name': 'Owner Telephone',
            'data_type': 'string',
        }, {
            'column_name': 'building_count',
            'table_name': 'PropertyState',
            'display_name': 'Building Count',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'year_built',
            'table_name': 'PropertyState',
            'display_name': 'Year Built',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'recent_sale_date',
            'table_name': 'PropertyState',
            'display_name': 'Recent Sale Date',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'conditioned_floor_area',
            'table_name': 'PropertyState',
            'display_name': 'Conditioned Floor Area',
            'data_type': 'area',
            # 'type': 'number',
            # 'dbField': True,
        }, {
            'column_name': 'occupied_floor_area',
            'table_name': 'PropertyState',
            'display_name': 'Occupied Floor Area',
            'data_type': 'area',
            # 'type': 'number',
        }, {
            'column_name': 'owner_address',
            'table_name': 'PropertyState',
            'display_name': 'Owner Address',
            'data_type': 'string',
        }, {
            'column_name': 'owner_city_state',
            'table_name': 'PropertyState',
            'display_name': 'Owner City/State',
            'data_type': 'string',
        }, {
            'column_name': 'owner_postal_code',
            'table_name': 'PropertyState',
            'display_name': 'Owner Postal Code',
            'data_type': 'string',
        }, {
            'column_name': 'home_energy_score_id',
            'table_name': 'PropertyState',
            'display_name': 'Home Energy Score ID',
            'data_type': 'string',
        }, {
            'column_name': 'generation_date',
            'table_name': 'PropertyState',
            'display_name': 'PM Generation Date',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'release_date',
            'table_name': 'PropertyState',
            'display_name': 'PM Release Date',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'site_eui',
            'table_name': 'PropertyState',
            'display_name': 'Site EUI',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'site_eui_weather_normalized',
            'table_name': 'PropertyState',
            'display_name': 'Site EUI Weather Normalized',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'site_eui_modeled',
            'table_name': 'PropertyState',
            'display_name': 'Site EUI Modeled',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'source_eui',
            'table_name': 'PropertyState',
            'display_name': 'Source EUI',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'source_eui_weather_normalized',
            'table_name': 'PropertyState',
            'display_name': 'Source EUI Weather Normalized',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'source_eui_modeled',
            'table_name': 'PropertyState',
            'display_name': 'Source EUI Modeled',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'energy_alerts',
            'table_name': 'PropertyState',
            'display_name': 'Energy Alerts',
            'data_type': 'string',
        }, {
            'column_name': 'space_alerts',
            'table_name': 'PropertyState',
            'display_name': 'Space Alerts',
            'data_type': 'string',
        }, {
            'column_name': 'building_certification',
            'table_name': 'PropertyState',
            'display_name': 'Building Certification',
            'data_type': 'string',
        }, {
            'column_name': 'analysis_start_time',
            'table_name': 'PropertyState',
            'display_name': 'Analysis Start Time',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'analysis_end_time',
            'table_name': 'PropertyState',
            'display_name': 'Analysis End Time',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'analysis_state',
            'table_name': 'PropertyState',
            'display_name': 'Analysis State',
            'data_type': 'string',
        }, {
            'column_name': 'analysis_state_message',
            'table_name': 'PropertyState',
            'display_name': 'Analysis State Message',
            'data_type': 'string',
        }, {
            'column_name': 'number_properties',
            'table_name': 'TaxLotState',
            'display_name': 'Number Properties',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'block_number',
            'table_name': 'TaxLotState',
            'display_name': 'Block Number',
            'data_type': 'string',
        }, {
            'column_name': 'district',
            'table_name': 'TaxLotState',
            'display_name': 'District',
            'data_type': 'string',
        }
    ]
    organization = models.ForeignKey(SuperOrganization, blank=True, null=True)
    column_name = models.CharField(max_length=512, db_index=True)
    # name of the table which the column name applies, if the column name
    # is a db field. Options now are only PropertyState and TaxLotState
    table_name = models.CharField(max_length=512, blank=True, db_index=True)

    display_name = models.CharField(max_length=512, blank=True)
    data_type = models.CharField(max_length=64, default='None')

    # TODO: decide if we need this? I don't think I do.
    # If exclude_from_mapping, then the column will not be used as mapping suggestions
    # exclude_from_mapping = models.BooleanField(default=False)

    unit = models.ForeignKey(Unit, blank=True, null=True)
    enum = models.ForeignKey(Enum, blank=True, null=True)
    is_extra_data = models.BooleanField(default=False)
    import_file = models.ForeignKey('data_importer.ImportFile', blank=True, null=True)
    units_pint = models.CharField(max_length=64, blank=True, null=True)

    shared_field_type = models.IntegerField(choices=SHARED_FIELD_TYPES, default=SHARED_NONE)

    # Do not enable this until running through the database and merging the columns down.
    # BUT first, make sure to add an import file ID into the column class.
    # class Meta:
    #     unique_together = (
    #         'organization', 'column_name', 'is_extra_data', 'table_name', 'import_file')

    def __unicode__(self):
        return u'{} - {}'.format(self.pk, self.column_name)

    def clean(self):
        # Don't allow Columns that are not extra_data and not a field in the database
        if (not self.is_extra_data) and self.table_name:
            # if it isn't extra data and the table_name IS set, then it must be part of the database fields
            found = False
            for c in Column.DATABASE_COLUMNS:
                if self.table_name == c['table_name'] and self.column_name == c['column_name']:
                    found = True

            if not found:
                raise ValidationError(
                    {'is_extra_data': _(
                        'Column \'%s\':\'%s\' is not marked as extra data, but the field is not in the database') % (
                        self.table_name, self.column_name)})

    @staticmethod
    def create_mappings_from_file(filename, organization, user, import_file_id=None):
        """
        Load the mappings in from a file in a very specific file format. The columns in the file
        must be:

            1. raw field
            2. table name
            3. field name
            4. field display name
            5. field data type
            6. field unit type

        :param filename: string, absolute path and name of file to load
        :param organization: id, organization id
        :param user: id, user id
        :param import_file_id: Integer, If passed, will cache the column mappings data into
                               the import_file_id object.

        :return: ColumnMapping, True
        """

        mappings = []
        if os.path.isfile(filename):
            with open(filename, 'rU') as csvfile:
                for row in csv.reader(csvfile):
                    data = {
                        "from_field": row[0],
                        "to_table_name": row[1],
                        "to_field": row[2],
                        # "to_display_name": row[3],
                        # "to_data_type": row[4],
                        # "to_unit_type": row[5],
                    }
                    mappings.append(data)
        else:
            raise Exception("Mapping file does not exist: {}".format(filename))

        if len(mappings) == 0:
            raise Exception("No mappings in file: {}".format(filename))
        else:
            return Column.create_mappings(mappings, organization, user, import_file_id)

    @staticmethod
    def create_mappings(mappings, organization, user, import_file_id=None):
        """
        Create the mappings for an organization and a user based on a simple
        array of array object.

        :param mappings: dict, dictionary containing mapping information
        :param organization: inst, organization object
        :param user: inst, User object
        :param import_file_id: integer, If passed, will cache the column mappings data into the
                               import_file_id object.

        :return Boolean, True is data are saved in the ColumnMapping table in the database

        .. note:

            Note that as of 09/15/2016 - extra data still needs to be defined in the mappings, it
            will no longer magically appear in the extra_data field if the user did not specify how
            to map it.

        .. example:

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
        """

        # initialize a cache to store the mappings
        cache_column_mapping = []

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
                    _log.debug('ColumnMapping.MultipleObjectsReturned in create_mappings')
                    # handle the special edge-case where remove dupes does not get
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

                cache_column_mapping.append(
                    {
                        'from_field': mapping['from_field'],
                        'from_units': mapping.get('from_units'),
                        'to_field': mapping['to_field'],
                        'to_table_name': mapping['to_table_name'],
                    }
                )
            else:
                raise TypeError("Mapping object needs to be of type dict")

        # save off the cached mappings into the file id that was passed
        if import_file_id:
            from seed.models import ImportFile
            import_file = ImportFile.objects.get(id=import_file_id)
            import_file.save_cached_mapped_columns(cache_column_mapping)
            import_file.save()

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
                        'from_units': 'kBtu/ft**2/year', # optional
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

        # Container to store the dicts with the Column object
        new_data = []

        for field in fields:
            new_field = field

            # Check if the extra_data field in the model object is a database column
            is_extra_data = True
            for c in Column.DATABASE_COLUMNS:
                if field['to_table_name'] == c['table_name'] and field['to_field'] == c['column_name']:
                    is_extra_data = False
                    break

            try:
                to_org_col, _ = Column.objects.get_or_create(
                    organization=organization,
                    column_name=field['to_field'],
                    table_name=field['to_table_name'],
                    is_extra_data=is_extra_data
                )
            except Column.MultipleObjectsReturned:
                _log.debug("More than one to_column found for {}.{}".format(field['to_table_name'],
                                                                            field['to_field']))
                # raise Exception("Cannot handle more than one to_column returned for {}.{}".format(
                #     field['to_field'], field['to_table_name']))

                # TODO: write something to remove the duplicate columns
                to_org_col = Column.objects.filter(organization=organization,
                                                   column_name=field['to_field'],
                                                   table_name=field['to_table_name'],
                                                   is_extra_data=is_extra_data).first()
                _log.debug("Grabbing the first to_column")

            try:
                # the from column is the field in the import file, thus the table_name needs to be
                # blank. Eventually need to handle passing in import_file_id
                from_org_col, _ = Column.objects.get_or_create(
                    organization=organization,
                    table_name__in=[None, ''],
                    column_name=field['from_field'],
                    units_pint=field.get('from_units'),  # might be None
                    is_extra_data=False  # data from header rows in the files are NEVER extra data
                )
            except Column.MultipleObjectsReturned:
                _log.debug(
                    "More than one from_column found for {}.{}".format(field['to_table_name'],
                                                                       field['to_field']))

                # TODO: write something to remove the duplicate columns
                from_org_col = Column.objects.filter(organization=organization,
                                                     table_name__in=[None, ''],
                                                     column_name=field['from_field'],
                                                     units_pint=field.get('from_units'),  # might be None
                                                     is_extra_data=is_extra_data).first()
                _log.debug("Grabbing the first from_column")

            new_field['to_column_object'] = select_col_obj(field['to_field'], field['to_table_name'], to_org_col)
            new_field['from_column_object'] = select_col_obj(field['from_field'], "", from_org_col)
            new_data.append(new_field)

        return new_data

    @staticmethod
    def save_column_names(model_obj):
        """Save unique column names for extra_data in this organization.

        This is a record of all the extra_data keys we have ever seen
        for a particular organization.

        :param model_obj: model_obj instance (either PropertyState or TaxLotState).
        """
        db_columns = Column.retrieve_db_field_table_and_names_from_db_tables()
        for key in model_obj.extra_data:
            # Check if the extra_data field in the model object is a database column
            is_extra_data = (model_obj.__class__.__name__, key[:511]) not in db_columns

            # handle the special edge-case where an old organization may have duplicate columns
            # in the database. We should make this a migration in the future and put a validation
            # in the db.
            for i in range(0, 5):
                while True:
                    try:
                        Column.objects.get_or_create(
                            table_name=model_obj.__class__.__name__,
                            column_name=key[:511],
                            is_extra_data=is_extra_data,
                            organization=model_obj.organization,
                        )
                    except Column.MultipleObjectsReturned:
                        _log.debug(
                            "Column.MultipleObjectsReturned for {} in save_column_names".format(
                                key[:511]))

                        columns = Column.objects.filter(table_name=model_obj.__class__.__name__,
                                                        column_name=key[:511],
                                                        is_extra_data=is_extra_data,
                                                        organization=model_obj.organization)
                        for c in columns:
                            if not ColumnMapping.objects.filter(Q(column_raw=c) | Q(column_mapped=c)).exists():
                                _log.debug("Deleting column object {}".format(c.column_name))
                                c.delete()

                        # Check if there are more than one column still
                        if Column.objects.filter(
                                table_name=model_obj.__class__.__name__,
                                column_name=key[:511],
                                is_extra_data=is_extra_data,
                                organization=model_obj.organization).count() > 1:
                            raise Exception(
                                "Could not fix duplicate columns for {}. Contact dev team").format(
                                key)

                        continue

                    break

    def to_dict(self):
        """
        Convert the column object to a dictionary

        :return: dict
        """

        c = {
            'pk': self.id,
            'id': self.id,
            'organization_id': self.organization.id,
            'table_name': self.table_name,
            'column_name': self.column_name,
            'is_extra_data': self.is_extra_data
        }
        if self.unit:
            c['unit_name'] = self.unit.unit_name
            c['unit_type'] = self.unit.unit_type
        else:
            c['unit_name'] = None
            c['unit_type'] = None

        return c

    @staticmethod
    def delete_all(organization):
        """
        Delete all the columns for an organization. Note that this will invalidate all the
        data that is in the extra_data fields of the inventory and is irreversible.

        :param organization: instance, Organization
        :return: [int, int] Number of columns, column_mappings records that were deleted
        """
        cm_delete_count, _ = ColumnMapping.objects.filter(super_organization=organization).delete()
        c_count, _ = Column.objects.filter(organization=organization).delete()
        return [c_count, cm_delete_count]

    @staticmethod
    def retrieve_db_types():
        """
        return the data types for the database columns in the format of:

        Example:
        {
          "field_name": "data_type",
          "field_name_2": "data_type_2",
          "address_line_1": "string",
        }

        :return: dict
        """
        columns = copy.deepcopy(Column.DATABASE_COLUMNS)

        MAP_TYPES = {
            'number': 'float',
            'float': 'float',
            'integer': 'integer',
            'string': 'string',
            'datetime': 'datetime',
            'date': 'date',
            'boolean': 'boolean',
            'area': 'float',
            'eui': 'float'
        }

        types = OrderedDict()
        for c in columns:
            try:
                types[c['column_name']] = MAP_TYPES[c['data_type']]
            except KeyError:
                print "could not find data_type for %s" % c
                types[c['column_name']] = ''

        return {"types": types}

    @staticmethod
    def retrieve_db_fields(org_id):
        """
        return the fields in the database regardless of properties or taxlots. For example, there is an address_line_1
        in both the TaxLotState and the PropertyState. The command below will take the `set` to remove the duplicates.

        [ "address_line_1", "gross_floor_area", ... ]
        :param org_id: int, Organization ID
        :return: list
        """

        result = list(
            set(list(Column.objects.filter(organization_id=org_id, is_extra_data=False).order_by('column_name').exclude(
                table_name='').exclude(table_name=None).values_list('column_name', flat=True))))

        return result

    @staticmethod
    def retrieve_db_field_table_and_names_from_db_tables():
        """
        Similar to keys, except it returns a list of tuples of the columns that are in the database

        .. code:
            [
              ('PropertyState', 'address_line_1'),
              ('PropertyState', 'address_line_2'),
              ('PropertyState', 'building_certification'),
              ('PropertyState', 'building_count'),
              ('TaxLotState', 'address_line_1'),
              ('TaxLotState', 'address_line_2'),
              ('TaxLotState', 'block_number'),
              ('TaxLotState', 'city'),
              ('TaxLotState', 'jurisdiction_tax_lot_id'),
            ]

        :return:list of tuples
        """
        result = set()
        for d in Column.retrieve_db_fields_from_db_tables():
            result.add((d['table_name'], d['column_name']))

        return list(sorted(result))

    @staticmethod
    def retrieve_db_field_name_for_hash_comparison():
        """
        Names only of the columns in the database (fields only, not extra data), indpendent of inventory type.
        These fields are used for generating an MD5 hash to quickly check if the data are the same across
        multiple records. Note that this ignores extra_data. The result is a superset of all the fields that are used
        in the database across all of the intentory types of interest.

        :return: list, names of columns, independent of inventory type.
        """
        result = []
        columns = Column.retrieve_db_fields_from_db_tables()
        for c in columns:
            result.append(c['column_name'])

        return list(sorted(set(result)))

    @staticmethod
    def retrieve_db_fields_from_db_tables():
        """
        Return the list of database fields that are in the models. This is independent of what are in the
        Columns table.

        :return:
        """
        all_columns = []
        for f in apps.get_model('seed', 'PropertyState')._meta.fields + \
                apps.get_model('seed', 'TaxLotState')._meta.fields + \
                apps.get_model('seed', 'Property')._meta.fields + \
                apps.get_model('seed', 'TaxLot')._meta.fields:

            # this remove import_file and others
            if f.get_internal_type() == 'ForeignKey':
                continue

            if f.name not in Column.COLUMN_EXCLUDE_FIELDS:
                dt = f.get_internal_type() if f.get_internal_type else 'string',
                dt = Column.INTERNAL_TYPE_TO_DATA_TYPE[dt[0]]
                all_columns.append(

                    {
                        'table_name': f.model.__name__,
                        'column_name': f.name,
                        'data_type': dt,
                    }

                )
        return all_columns

    @staticmethod
    def retrieve_mapping_columns(org_id):
        """
        Retrieve all the columns that are for mapping for an organization in a dictionary.

        :param org_id: org_id, Organization ID
        :return: list, list of dict
        """
        columns_db = Column.objects.filter(organization_id=org_id).exclude(table_name='').exclude(table_name=None)
        columns = []
        for c in columns_db:
            if c.column_name in Column.COLUMN_EXCLUDE_FIELDS or c.column_name in Column.EXCLUDED_MAPPING_FIELDS:
                continue

            # Eventually move this over to Column serializer directly
            new_c = model_to_dict(c)

            del new_c['shared_field_type']
            new_c['sharedFieldType'] = c.get_shared_field_type_display()

            if (new_c['table_name'], new_c['column_name']) in Column.PINNED_COLUMNS:
                new_c['pinnedLeft'] = True

            if not new_c['display_name']:
                new_c['display_name'] = titlecase(new_c['column_name'])

            del new_c['import_file']
            del new_c['organization']
            del new_c['enum']
            del new_c['units_pint']
            del new_c['unit']

            columns.append(new_c)

        return columns

    @staticmethod
    def retrieve_all(org_id, inventory_type, only_used):
        """
        Retrieve all the columns for an organization. This method will query for all the columns in the
        database assigned to the organization. It will then go through and cleanup the names to ensure that
        there are no duplicates.

        :param org_id: Organization ID
        :param inventory_type: Inventory Type (property|taxlot) from the requester. This sets the related columns correctly
        :param only_used: View only the used columns that exist in the Column's table

        :return: dict
        """
        # Grab all the columns out of the database for the organization that are assigned to a table_name
        # Order extra_data last so that extra data duplicate-checking will happen after processing standard columns
        columns_db = Column.objects.filter(organization_id=org_id).exclude(table_name='').exclude(
            table_name=None).order_by('is_extra_data', 'column_name')
        columns = []
        for c in columns_db:
            # Eventually move this over to Column serializer directly
            new_c = model_to_dict(c)

            del new_c['shared_field_type']
            new_c['sharedFieldType'] = c.get_shared_field_type_display()

            if (new_c['table_name'], new_c['column_name']) in Column.PINNED_COLUMNS:
                new_c['pinnedLeft'] = True

            if not new_c['display_name']:
                new_c['display_name'] = titlecase(new_c['column_name'])

            # set the name of the column which is a special field because it can take on a relationship
            # with the table_name and have an _extra associated with it
            new_c['name'] = new_c['column_name']

            # Related fields
            new_c['related'] = not (inventory_type.lower() in new_c['table_name'].lower())

            # check if the column name exists in the other table (and not extra data).
            # Example, gross_floor_area is a core field, but can be an extra field in taxlot, meaning that the other one
            # needs to be tagged something else. (prepended with tax_ or property_).
            if new_c['related']:
                # if it is related then have the display name show the other table
                new_c['display_name'] = new_c['display_name'] + ' (%s)' % INVENTORY_DISPLAY[new_c['table_name']]

                # This only pertains to the tables: PropertyState and TaxLotState
                if 'State' in new_c['table_name']:
                    if Column.objects.filter(organization_id=org_id,
                                             table_name=COLUMN_OPPOSITE_TABLE[new_c['table_name']],
                                             column_name=new_c['column_name'],
                                             is_extra_data=False).exists():
                        new_c['name'] = "%s_%s" % (
                            INVENTORY_MAP_OPPOSITE_PREPEND[inventory_type.lower()], new_c['name'])

            if new_c['is_extra_data']:
                # Avoid name conflicts with protected front-end columns and extra_data columns
                if new_c['name'] in ['id', 'notes_count']:
                    new_c['name'] += '_extra'

                # add _extra if the column is already in the list for the other table
                while any(col['name'] == new_c['name'] and col['table_name'] != new_c['table_name'] for col in columns):
                    new_c['name'] += '_extra'

            # remove a bunch of fields that are not needed in the list of columns
            del new_c['import_file']
            del new_c['organization']
            del new_c['enum']
            del new_c['units_pint']
            del new_c['unit']

            # only add the column if it is in a ColumnMapping object
            if only_used:
                if ColumnMapping.objects.filter(column_mapped=c).exists():
                    columns.append(new_c)
            else:
                columns.append(new_c)

        # import json
        # print json.dumps(columns, indent=2)

        # validate that the field 'name' is unique.
        uniq = set()
        for c in columns:
            if (c['table_name'], c['column_name']) in uniq:
                raise Exception("Duplicate name '{}' found in columns".format(c['name']))
            else:
                uniq.add((c['table_name'], c['column_name']))

        return columns

    @staticmethod
    def retrieve_all_by_tuple(org_id):
        """
        Return list of all columns for an organization as a tuple.

        .. code:
            [
              ('PropertyState', 'address_line_1'),
              ('PropertyState', 'address_line_2'),
              ('PropertyState', 'building_certification'),
              ('PropertyState', 'building_count'),
              ('TaxLotState', 'address_line_1'),
              ('TaxLotState', 'address_line_2'),
              ('TaxLotState', 'block_number'),
              ('TaxLotState', 'city'),
              ('TaxLotState', 'jurisdiction_tax_lot_id'),
            ]

        :param org_id: int, Organization ID
        :return: list of tuples
        """
        result = []
        for col in Column.retrieve_all(org_id, 'PropertyState', False):
            result.append((col['table_name'], col['column_name']))

        return result


def validate_model(sender, **kwargs):
    if 'raw' in kwargs and not kwargs['raw']:
        kwargs['instance'].full_clean()


pre_save.connect(validate_model, sender=Column)


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

    def to_dict(self):
        """
        Convert the ColumnMapping object to a dictionary

        :return: dict
        """

        c = {
            'pk': self.id,
            'id': self.id
        }
        if self.user:
            c['user_id'] = self.user.id
        else:
            c['user_id'] = None
        c['source_type'] = self.source_type
        c['organization_id'] = self.super_organization.id
        if self.column_raw and self.column_raw.first():
            c['from_column'] = self.column_raw.first().to_dict()
        else:
            c['from_column'] = None

        if self.column_mapped and self.column_mapped.first():
            c['to_column'] = self.column_mapped.first().to_dict()
        else:
            c['to_column'] = None

        return c

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

        Use this when actually performing mapping between data sources, but only
        call it after all of the mappings have been saved to the ``ColumnMapping``
        table.

        ..code:

            {
                u'Wookiee': (u'PropertyState', u'Dothraki', 'DisplayName', True),
                u'Ewok': (u'TaxLotState', u'Hattin', 'DisplayName', True),
                u'eui': (u'PropertyState', u'site_eui', 'DisplayName', True),
                u'address': (u'TaxLotState', u'address', 'DisplayName', True)
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

            key = cm.column_raw.all().values_list('table_name', 'column_name', 'display_name', 'is_extra_data')
            value = cm.column_mapped.all().values_list('table_name', 'column_name', 'display_name', 'is_extra_data')

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
        for k, v in data.iteritems():
            tables.add(v[0])

        # initialize the new container to store the results
        # (there has to be a better way of doing this... not enough time)
        container = {}
        for t in tables:
            container[t] = {}

        for k, v in data.iteritems():
            container[v[0]][k] = v

        # Container will be in the format:
        #
        # container = {
        #     u'PropertyState': {
        #         u'Wookiee': (u'PropertyState', u'Dothraki'),
        #         u'eui': (u'PropertyState', u'site_eui'),
        #     },
        #     u'TaxLotState': {
        #         u'address': (u'TaxLotState', u'address'),
        #         u'Ewok': (u'TaxLotState', u'Hattin'),
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
