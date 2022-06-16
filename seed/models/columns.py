# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

import copy
import csv
import logging
import os.path
from collections import OrderedDict
from typing import Literal, Optional

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models.column_mappings import ColumnMapping
from seed.models.models import Unit

INVENTORY_DISPLAY = {
    'PropertyState': 'Property',
    'TaxLotState': 'Tax Lot',
    'Property': 'Property',
    'TaxLot': 'Tax Lot',
}
_log = logging.getLogger(__name__)


class Column(models.Model):
    """The name of a column for a given organization."""
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

    # Do not return these columns to the front end -- when using the tax_lot_properties
    # get_related method.
    EXCLUDED_COLUMN_RETURN_FIELDS = [
        'hash_object',
        'normalized_address',
        # Records below are old and should not be used
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

    QUANTITY_UNIT_COLUMNS = [
        ('PropertyState', 'gross_floor_area'),
        ('PropertyState', 'occupied_floor_area'),
        ('PropertyState', 'conditioned_floor_area'),
        ('PropertyState', 'site_eui'),
        ('PropertyState', 'site_eui_modeled'),
        ('PropertyState', 'site_eui_weather_normalized'),
        ('PropertyState', 'source_eui'),
        ('PropertyState', 'source_eui_modeled'),
        ('PropertyState', 'source_eui_weather_normalized'),
        ('PropertyState', 'total_ghg_emissions'),
        ('PropertyState', 'total_marginal_ghg_emissions'),
        ('PropertyState', 'total_ghg_emissions_intensity'),
        ('PropertyState', 'total_marginal_ghg_emissions_intensity'),
    ]

    COLUMN_MERGE_FAVOR_NEW = 0
    COLUMN_MERGE_FAVOR_EXISTING = 1
    COLUMN_MERGE_PROTECTION = [
        (COLUMN_MERGE_FAVOR_NEW, 'Favor New'),
        (COLUMN_MERGE_FAVOR_EXISTING, 'Favor Existing')
    ]

    # These fields are excluded from being returned to the front end via the API and the
    # Column.retrieve_all method. Note that not all the endpoints are respecting this at the moment.
    EXCLUDED_API_FIELDS = [
        'normalized_address',
    ]

    # These are the columns that are removed when looking to see if the records are the same
    COLUMN_EXCLUDE_FIELDS = [
        'bounding_box',
        'centroid',
        'created',
        'data_state',
        'extra_data',
        'geocoding_confidence',
        'id',
        'import_file',
        'long_lat',
        'merge_state',
        'source_type',
        'updated',
    ] + EXCLUDED_COLUMN_RETURN_FIELDS

    EXCLUDED_RENAME_TO_FIELDS = [
        'lot_number',
        'latitude',
        'longitude',
        'year_built',
        'property_footprint',
        'campus',
        'created',
        'updated',
    ] + COLUMN_EXCLUDE_FIELDS

    EXCLUDED_RENAME_FROM_FIELDS = [
        'campus',
        'lot_number',
        'year_built',
        'property_footprint',
        'taxlot_footprint',
    ] + COLUMN_EXCLUDE_FIELDS

    # These are fields that should not be mapped to, ever.
    EXCLUDED_MAPPING_FIELDS = [
        'created',
        'extra_data',
        'lot_number',
        'normalized_address',
        'updated',
    ]

    # These are columns that should not be offered as suggestions during mapping
    UNMAPPABLE_PROPERTY_FIELDS = [
        'campus',
        'created',
        'geocoding_confidence',
        'lot_number',
        'updated'
    ]
    UNMAPPABLE_TAXLOT_FIELDS = [
        'created',
        'geocoding_confidence',
        'updated'
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
        'PolygonField': 'geometry',
        'PointField': 'geometry',
    }

    # These are the default columns (also known as the fields in the database)
    DATABASE_COLUMNS = [
        {
            'column_name': 'pm_property_id',
            'table_name': 'PropertyState',
            'display_name': 'PM Property ID',
            'column_description': 'PM Property ID',
            'data_type': 'string',
        }, {
            'column_name': 'pm_parent_property_id',
            'table_name': 'PropertyState',
            'display_name': 'PM Parent Property ID',
            'column_description': 'PM Parent Property ID',
            'data_type': 'string',
        }, {
            'column_name': 'jurisdiction_tax_lot_id',
            'table_name': 'TaxLotState',
            'display_name': 'Jurisdiction Tax Lot ID',
            'column_description': 'Jurisdiction Tax Lot ID',
            'data_type': 'string',
        }, {
            'column_name': 'jurisdiction_property_id',
            'table_name': 'PropertyState',
            'display_name': 'Jurisdiction Property ID',
            'column_description': 'Jurisdiction Property ID',
            'data_type': 'string',
        }, {
            'column_name': 'ulid',
            'table_name': 'TaxLotState',
            'display_name': 'ULID',
            'column_description': 'ULID',
            'data_type': 'string',
        }, {
            'column_name': 'ubid',
            'table_name': 'PropertyState',
            'display_name': 'UBID',
            'column_description': 'UBID',
            'data_type': 'string',
        }, {
            'column_name': 'custom_id_1',
            'table_name': 'PropertyState',
            'display_name': 'Custom ID 1',
            'column_description': 'Custom ID 1',
            'data_type': 'string',
        }, {
            'column_name': 'custom_id_1',
            'table_name': 'TaxLotState',
            'display_name': 'Custom ID 1',
            'column_description': 'Custom ID 1',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_1',
            'table_name': 'PropertyState',
            'display_name': 'Address Line 1',
            'column_description': 'Address Line 1',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_1',
            'table_name': 'TaxLotState',
            'display_name': 'Address Line 1',
            'column_description': 'Address Line 1',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_2',
            'table_name': 'PropertyState',
            'display_name': 'Address Line 2',
            'column_description': 'Address Line 2',
            'data_type': 'string',
        }, {
            'column_name': 'address_line_2',
            'table_name': 'TaxLotState',
            'display_name': 'Address Line 2',
            'column_description': 'Address Line 2',
            'data_type': 'string',
        }, {
            'column_name': 'city',
            'table_name': 'PropertyState',
            'display_name': 'City',
            'column_description': 'City',
            'data_type': 'string',
        }, {
            'column_name': 'city',
            'table_name': 'TaxLotState',
            'display_name': 'City',
            'column_description': 'City',
            'data_type': 'string',
        }, {
            'column_name': 'state',
            'table_name': 'PropertyState',
            'display_name': 'State',
            'column_description': 'State',
            'data_type': 'string',
        }, {
            'column_name': 'state',
            'table_name': 'TaxLotState',
            'display_name': 'State',
            'column_description': 'State',
            'data_type': 'string',
        }, {
            # This should never be mapped to!
            'column_name': 'normalized_address',
            'table_name': 'PropertyState',
            'display_name': 'Normalized Address',
            'column_description': 'Normalized Address',
            'data_type': 'string',
        }, {
            # This should never be mapped to!
            'column_name': 'normalized_address',
            'table_name': 'TaxLotState',
            'display_name': 'Normalized Address',
            'column_description': 'Normalized Address',
            'data_type': 'string',
        }, {
            'column_name': 'postal_code',
            'table_name': 'PropertyState',
            'display_name': 'Postal Code',
            'column_description': 'Postal Code',
            'data_type': 'string',
        }, {
            'column_name': 'postal_code',
            'table_name': 'TaxLotState',
            'display_name': 'Postal Code',
            'column_description': 'Postal Code',
            'data_type': 'string',
        }, {
            # This field should never be mapped to!
            'column_name': 'lot_number',
            'table_name': 'PropertyState',
            'display_name': 'Associated Tax Lot ID',
            'column_description': 'Associated Tax Lot ID',
            'data_type': 'string',
        }, {
            'column_name': 'property_name',
            'table_name': 'PropertyState',
            'display_name': 'Property Name',
            'column_description': 'Property Name',
            'data_type': 'string',
        }, {
            'column_name': 'latitude',
            'table_name': 'PropertyState',
            'display_name': 'Latitude',
            'column_description': 'Latitude',
            'data_type': 'number',
        }, {
            'column_name': 'longitude',
            'table_name': 'PropertyState',
            'display_name': 'Longitude',
            'column_description': 'Longitude',
            'data_type': 'number',
        }, {
            'column_name': 'latitude',
            'table_name': 'TaxLotState',
            'display_name': 'Latitude',
            'column_description': 'Latitude',
            'data_type': 'number',
        }, {
            'column_name': 'longitude',
            'table_name': 'TaxLotState',
            'display_name': 'Longitude',
            'column_description': 'Longitude',
            'data_type': 'number',
        }, {
            'column_name': 'geocoding_confidence',
            'table_name': 'PropertyState',
            'display_name': 'Geocoding Confidence',
            'column_description': 'Geocoding Confidence',
            'data_type': 'string',
        }, {
            'column_name': 'geocoding_confidence',
            'table_name': 'TaxLotState',
            'display_name': 'Geocoding Confidence',
            'column_description': 'Geocoding Confidence',
            'data_type': 'string',
        }, {
            'column_name': 'property_footprint',
            'table_name': 'PropertyState',
            'display_name': 'Property Footprint',
            'column_description': 'Property Footprint',
            'data_type': 'geometry',
        }, {
            'column_name': 'taxlot_footprint',
            'table_name': 'TaxLotState',
            'display_name': 'Tax Lot Footprint',
            'column_description': 'Tax Lot Footprint',
            'data_type': 'geometry',
        }, {
            'column_name': 'campus',
            'table_name': 'Property',
            'display_name': 'Campus',
            'column_description': 'Campus',
            'data_type': 'boolean',
            # 'type': 'boolean',
        }, {
            'column_name': 'updated',
            'table_name': 'PropertyState',
            'display_name': 'Updated',
            'column_description': 'Updated',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'created',
            'table_name': 'PropertyState',
            'display_name': 'Created',
            'column_description': 'Created',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'updated',
            'table_name': 'TaxLotState',
            'display_name': 'Updated',
            'column_description': 'Updated',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'created',
            'table_name': 'TaxLotState',
            'display_name': 'Created',
            'column_description': 'Created',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'gross_floor_area',
            'table_name': 'PropertyState',
            'display_name': 'Gross Floor Area',
            'column_description': 'Gross Floor Area',
            'data_type': 'area',
            # 'type': 'number',
        }, {
            'column_name': 'use_description',
            'table_name': 'PropertyState',
            'display_name': 'Use Description',
            'column_description': 'Use Description',
            'data_type': 'string',
        }, {
            'column_name': 'energy_score',
            'table_name': 'PropertyState',
            'display_name': 'ENERGY STAR Score',
            'column_description': 'ENERGY STAR Score',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'property_notes',
            'table_name': 'PropertyState',
            'display_name': 'Property Notes',
            'column_description': 'Property Notes',
            'data_type': 'string',
        }, {
            'column_name': 'property_type',
            'table_name': 'PropertyState',
            'display_name': 'Property Type',
            'column_description': 'Property Type',
            'data_type': 'string',
        }, {
            'column_name': 'year_ending',
            'table_name': 'PropertyState',
            'display_name': 'Year Ending',
            'column_description': 'Year Ending',
            'data_type': 'date',
        }, {
            'column_name': 'owner',
            'table_name': 'PropertyState',
            'display_name': 'Owner',
            'column_description': 'Owner',
            'data_type': 'string',
        }, {
            'column_name': 'owner_email',
            'table_name': 'PropertyState',
            'display_name': 'Owner Email',
            'column_description': 'Owner Email',
            'data_type': 'string',
        }, {
            'column_name': 'owner_telephone',
            'table_name': 'PropertyState',
            'display_name': 'Owner Telephone',
            'column_description': 'Owner Telephone',
            'data_type': 'string',
        }, {
            'column_name': 'building_count',
            'table_name': 'PropertyState',
            'display_name': 'Building Count',
            'column_description': 'Building Count',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'year_built',
            'table_name': 'PropertyState',
            'display_name': 'Year Built',
            'column_description': 'Year Built',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'recent_sale_date',
            'table_name': 'PropertyState',
            'display_name': 'Recent Sale Date',
            'column_description': 'Recent Sale Date',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'conditioned_floor_area',
            'table_name': 'PropertyState',
            'display_name': 'Conditioned Floor Area',
            'column_description': 'Conditioned Floor Area',
            'data_type': 'area',
            # 'type': 'number',
            # 'dbField': True,
        }, {
            'column_name': 'occupied_floor_area',
            'table_name': 'PropertyState',
            'display_name': 'Occupied Floor Area',
            'column_description': 'Occupied Floor Area',
            'data_type': 'area',
            # 'type': 'number',
        }, {
            'column_name': 'owner_address',
            'table_name': 'PropertyState',
            'display_name': 'Owner Address',
            'column_description': 'Owner Address',
            'data_type': 'string',
        }, {
            'column_name': 'owner_city_state',
            'table_name': 'PropertyState',
            'display_name': 'Owner City/State',
            'column_description': 'Owner City/State',
            'data_type': 'string',
        }, {
            'column_name': 'owner_postal_code',
            'table_name': 'PropertyState',
            'display_name': 'Owner Postal Code',
            'column_description': 'Owner Postal Code',
            'data_type': 'string',
        }, {
            'column_name': 'home_energy_score_id',
            'table_name': 'PropertyState',
            'display_name': 'Home Energy Score ID',
            'column_description': 'Home Energy Score ID',
            'data_type': 'string',
        }, {
            'column_name': 'generation_date',
            'table_name': 'PropertyState',
            'display_name': 'PM Generation Date',
            'column_description': 'PM Generation Date',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'release_date',
            'table_name': 'PropertyState',
            'display_name': 'PM Release Date',
            'column_description': 'PM Release Date',
            'data_type': 'datetime',
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        }, {
            'column_name': 'site_eui',
            'table_name': 'PropertyState',
            'display_name': 'Site EUI',
            'column_description': 'Site EUI',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'site_eui_weather_normalized',
            'table_name': 'PropertyState',
            'display_name': 'Site EUI Weather Normalized',
            'column_description': 'Site EUI Weather Normalized',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'site_eui_modeled',
            'table_name': 'PropertyState',
            'display_name': 'Site EUI Modeled',
            'column_description': 'Site EUI Modeled',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'source_eui',
            'table_name': 'PropertyState',
            'display_name': 'Source EUI',
            'column_description': 'Source EUI',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'source_eui_weather_normalized',
            'table_name': 'PropertyState',
            'display_name': 'Source EUI Weather Normalized',
            'column_description': 'Source EUI Weather Normalized',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'source_eui_modeled',
            'table_name': 'PropertyState',
            'display_name': 'Source EUI Modeled',
            'column_description': 'Source EUI Modeled',
            'data_type': 'eui',
            # 'type': 'number',
        }, {
            'column_name': 'energy_alerts',
            'table_name': 'PropertyState',
            'display_name': 'Energy Alerts',
            'column_description': 'Energy Alerts',
            'data_type': 'string',
        }, {
            'column_name': 'space_alerts',
            'table_name': 'PropertyState',
            'display_name': 'Space Alerts',
            'column_description': 'Space Alerts',
            'data_type': 'string',
        }, {
            'column_name': 'building_certification',
            'table_name': 'PropertyState',
            'display_name': 'Building Certification',
            'column_description': 'Building Certification',
            'data_type': 'string',
        }, {
            'column_name': 'number_properties',
            'table_name': 'TaxLotState',
            'display_name': 'Number Properties',
            'column_description': 'Number Properties',
            'data_type': 'integer',
            # 'type': 'number',
        }, {
            'column_name': 'block_number',
            'table_name': 'TaxLotState',
            'display_name': 'Block Number',
            'column_description': 'Block Number',
            'data_type': 'string',
        }, {
            'column_name': 'district',
            'table_name': 'TaxLotState',
            'display_name': 'District',
            'column_description': 'District',
            'data_type': 'string',
        }, {
            'column_name': 'egrid_subregion_code',
            'table_name': 'PropertyState',
            'display_name': 'eGRID Subregion Code',
            'column_description': 'eGRID Subregion Code',
            'data_type': 'string',
        }, {
            'column_name': 'total_ghg_emissions',
            'table_name': 'PropertyState',
            'display_name': 'Total GHG Emissions',
            'column_description': 'Total GHG Emissions',
            'data_type': 'number',
        }, {
            'column_name': 'total_marginal_ghg_emissions',
            'table_name': 'PropertyState',
            'display_name': 'Total Marginal GHG Emissions',
            'column_description': 'Total Marginal GHG Emissions',
            'data_type': 'number',
        }, {
            'column_name': 'total_ghg_emissions_intensity',
            'table_name': 'PropertyState',
            'display_name': 'Total GHG Emissions Intensity',
            'column_description': 'Total GHG Emissions Intensity',
            'data_type': 'number',
        }, {
            'column_name': 'total_marginal_ghg_emissions_intensity',
            'table_name': 'PropertyState',
            'display_name': 'Total Marginal GHG Emissions Intensity',
            'column_description': 'Total Marginal GHG Emissions Intensity',
            'data_type': 'number',
        }, {
            'column_name': 'property_timezone',
            'table_name': 'PropertyState',
            'display_name': 'Property Time Zone',
            'column_description': 'Time zone of the property',
            'data_type': 'string',
        }
    ]
    organization = models.ForeignKey(SuperOrganization, on_delete=models.CASCADE, blank=True, null=True)
    column_name = models.CharField(max_length=512, db_index=True)
    # name of the table which the column name applies, if the column name
    # is a db field. Options now are only PropertyState and TaxLotState
    table_name = models.CharField(max_length=512, blank=True, db_index=True)

    display_name = models.CharField(max_length=512, blank=True)
    column_description = models.TextField(max_length=1000, blank=True, default=None)
    data_type = models.CharField(max_length=64, default='None')

    # Add created/modified timestamps
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, blank=True, null=True)
    is_extra_data = models.BooleanField(default=False)
    is_matching_criteria = models.BooleanField(default=False)
    import_file = models.ForeignKey('data_importer.ImportFile', on_delete=models.CASCADE, blank=True, null=True)
    units_pint = models.CharField(max_length=64, blank=True, null=True)

    # 0 is deactivated. Order used to construct full address.
    geocoding_order = models.IntegerField(default=0, blank=False)

    shared_field_type = models.IntegerField(choices=SHARED_FIELD_TYPES, default=SHARED_NONE)

    # By default, when two records are merge the new data will take precedence over the existing
    # data, however, the user can override this on a column-by-column basis.
    merge_protection = models.IntegerField(choices=COLUMN_MERGE_PROTECTION,
                                           default=COLUMN_MERGE_FAVOR_NEW)

    recognize_empty = models.BooleanField(default=False)

    comstock_mapping = models.CharField(max_length=64, null=True, blank=True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'comstock_mapping'], name='unique_comstock_mapping'),
        ]

    def __str__(self):
        return '{} - {}:{}'.format(self.pk, self.table_name, self.column_name)

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
                        'Column \'%s\':\'%s\' is not a field in the database and not marked as extra data. Mark as extra data to save column.') % (
                        self.table_name, self.column_name)})

    def save(self, *args, **kwargs):
        if self.column_name and not self.column_description:
            self.column_description = self.column_name
        super().save(*args, **kwargs)

    def rename_column(self, new_column_name, force=False):
        """
        Rename the column and move all the data to the new column. This can move the
        data from a canonical field to an extra data field or vice versa. By default the
        column.

        :param new_column_name: string new name of column
        :param force: boolean force the overwrite of data in the column?
        :return:
        """
        from datetime import date as date_type
        from datetime import datetime as datetime_type

        from django.db.utils import DataError
        from pint.errors import DimensionalityError
        from quantityfield.units import ureg

        from seed.models.properties import PropertyState
        from seed.models.tax_lots import DATA_STATE_MATCHING, TaxLotState
        STR_TO_CLASS = {'TaxLotState': TaxLotState, 'PropertyState': PropertyState}

        def _serialize_for_extra_data(column_value):
            if isinstance(column_value, datetime_type):
                return column_value.isoformat()
            elif isinstance(column_value, date_type):
                return column_value.isoformat()
            elif isinstance(column_value, ureg.Quantity):
                return column_value.magnitude
            else:
                return column_value

        # restricted columns to rename to or from
        if new_column_name in self.EXCLUDED_RENAME_TO_FIELDS:
            return [False, "Column name '%s' is a reserved name. Choose another." % new_column_name]

        # Do not allow moving data out of the property based columns
        if self.column_name in self.EXCLUDED_RENAME_FROM_FIELDS or \
                self.table_name in ['Property', 'TaxLot']:
            return [False, "Can't move data out of reserved column '%s'" % self.column_name]

        try:
            with transaction.atomic():
                # check if the new_column already exists
                new_column = Column.objects.filter(table_name=self.table_name, column_name=new_column_name,
                                                   organization=self.organization)
                if len(new_column) > 0:
                    if not force:
                        return [False, 'New column already exists, specify overwrite data if desired']

                    new_column = new_column.first()

                    # update the fields in the new column to match the old columns
                    # new_column.display_name = self.display_name
                    # new_column.is_extra_data = self.is_extra_data
                    new_column.unit = self.unit
                    new_column.import_file = self.import_file
                    new_column.shared_field_type = self.shared_field_type
                    new_column.merge_protection = self.merge_protection
                    if not new_column.is_extra_data and not self.is_extra_data:
                        new_column.units_pint = self.units_pint
                    new_column.save()
                elif len(new_column) == 0:
                    # There isn't a column yet, so creating a new one
                    # New column will always have extra data.
                    # The units and related data are copied over to the new field
                    new_column = Column.objects.create(
                        organization=self.organization,
                        table_name=self.table_name,
                        column_name=new_column_name,
                        display_name=new_column_name,
                        column_description=new_column_name,
                        is_extra_data=True,
                        unit=self.unit,
                        # unit_pint  # Do not import unit_pint since that only works with db fields
                        import_file=self.import_file,
                        shared_field_type=self.shared_field_type,
                        merge_protection=self.merge_protection
                    )

                # go through the data and move it to the new field. I'm not sure yet on how long this is
                # going to take to run, so we may have to move this to a background task
                orig_data = STR_TO_CLASS[self.table_name].objects.filter(
                    organization=self.organization,
                    data_state=DATA_STATE_MATCHING
                )
                if new_column.is_extra_data:
                    if self.is_extra_data:
                        for datum in orig_data:
                            datum.extra_data[new_column.column_name] = datum.extra_data.get(self.column_name, None)
                            datum.extra_data.pop(self.column_name, None)
                            datum.save()
                    else:
                        for datum in orig_data:
                            column_value = _serialize_for_extra_data(getattr(datum, self.column_name))
                            datum.extra_data[new_column.column_name] = column_value
                            setattr(datum, self.column_name, None)
                            datum.save()
                else:
                    if self.is_extra_data:
                        for datum in orig_data:
                            setattr(datum, new_column.column_name, datum.extra_data.get(self.column_name, None))
                            datum.extra_data.pop(self.column_name, None)
                            datum.save()
                    else:
                        for datum in orig_data:
                            setattr(datum, new_column.column_name, getattr(datum, self.column_name))
                            setattr(datum, self.column_name, None)
                            datum.save()
        except (ValidationError, DataError):
            return [False, "The column data aren't formatted properly for the new column due to type constraints (e.g., Datatime, Quantities, etc.)."]
        except DimensionalityError:
            return [False, "The column data can't be converted to the new column due to conversion contraints (e.g., converting square feet to kBtu etc.)."]

        # Return true if this operation was successful
        return [True, 'Successfully renamed column and moved data']

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
            with open(filename, 'r', newline=None) as csvfile:
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
                        'from_field': 'eui',  # raw field in import file
                        'from_units': 'kBtu/ft**2/year', # pint-parsable units, optional
                        'to_field': 'energy_use_intensity',
                        'to_field_display_name': 'Energy Use Intensity',
                        'to_table_name': 'PropertyState',
                    },
                    {
                        'from_field': 'gfa',
                        'from_units': 'ft**2', # pint-parsable units, optional
                        'to_field': 'gross_floor_area',
                        'to_field_display_name': 'Gross Floor Area',
                        'to_table_name': 'PropertyState',
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
                if field['to_table_name'] == c['table_name'] and field['to_field'] == c[
                        'column_name']:
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
                from_org_col, _ = Column.objects.update_or_create(
                    organization=organization,
                    table_name='',
                    column_name=field['from_field'],
                    is_extra_data=False,  # Column objects representing raw/header rows are NEVER extra data
                    defaults={'units_pint': field.get('from_units', None)}
                )
            except Column.MultipleObjectsReturned:
                # We want to avoid the ambiguity of having multiple Column objects for a specific raw column.
                # To do that, delete all multiples along with any associated ColumnMapping objects.
                _log.debug(
                    "More than one from_column found for {}.{}".format(field['to_table_name'],
                                                                       field['to_field']))

                all_from_cols = Column.objects.filter(
                    organization=organization,
                    table_name='',
                    column_name=field['from_field'],
                    is_extra_data=False
                )

                ColumnMapping.objects.filter(column_raw__id__in=models.Subquery(all_from_cols.values('id'))).delete()
                all_from_cols.delete()

                from_org_col = Column.objects.create(
                    organization=organization,
                    table_name='',
                    units_pint=field.get('from_units', None),
                    column_name=field['from_field'],
                    column_description=field['from_field'],
                    is_extra_data=False  # Column objects representing raw/header rows are NEVER extra data
                )
                _log.debug("Creating a new from_column")

            new_field['to_column_object'] = select_col_obj(field['to_field'],
                                                           field['to_table_name'], to_org_col)
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
                            if not ColumnMapping.objects.filter(
                                    Q(column_raw=c) | Q(column_mapped=c)).exists():
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
        Return the data types for the database columns in the format of:

        .. code-block:: json

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
            'geometry': 'geometry',
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
                _log.error("could not find data_type for %s" % c)
                types[c['column_name']] = ''

        return {'types': types}

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
            set(list(Column.objects.filter(organization_id=org_id, is_extra_data=False).order_by(
                'column_name').exclude(
                table_name='').exclude(table_name=None).values_list('column_name', flat=True))))

        return result

    @staticmethod
    def retrieve_db_field_table_and_names_from_db_tables():
        """
        Similar to keys, except it returns a list of tuples of the columns that are in the database

        .. code-block:: json

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
        Names only of the columns in the database (fields only, not extra data), independent of inventory type.
        These fields are used for generating an MD5 hash to quickly check if the data are the same across
        multiple records. Note that this ignores extra_data. The result is a superset of all the fields that are used
        in the database across all of the inventory types of interest.

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
                apps.get_model('seed', 'TaxLotState')._meta.fields:

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
    def retrieve_mapping_columns(org_id, inventory_type=None):
        """
        Retrieve all the columns that are for mapping for an organization in a dictionary.

        :param org_id: org_id, Organization ID
        :param inventory_type: Inventory Type (property|taxlot) from the requester. This sets the related columns if requested.
        :return: list, list of dict
        """
        from seed.serializers.columns import ColumnSerializer

        columns_db = Column.objects.filter(organization_id=org_id).exclude(table_name='').exclude(
            table_name=None)
        columns = []
        for c in columns_db:
            if c.column_name in Column.COLUMN_EXCLUDE_FIELDS or c.column_name in Column.EXCLUDED_MAPPING_FIELDS:
                continue

            # Eventually move this over to Column serializer directly
            new_c = ColumnSerializer(c).data

            if inventory_type:
                related = not (inventory_type.lower() in new_c['table_name'].lower())
                if related:
                    continue
                if inventory_type == 'property' and c.column_name in Column.UNMAPPABLE_PROPERTY_FIELDS:
                    continue
                elif inventory_type == 'taxlot' and c.column_name in Column.UNMAPPABLE_TAXLOT_FIELDS:
                    continue

            new_c['sharedFieldType'] = new_c['shared_field_type']
            del new_c['shared_field_type']

            if (new_c['table_name'], new_c['column_name']) in Column.PINNED_COLUMNS:
                new_c['pinnedLeft'] = True

            # If no display name, use the column name (this is the display name as it was typed
            # during mapping)
            if not new_c['display_name']:
                new_c['display_name'] = new_c['column_name']

            # If no column_description, use the column name (this is the display name as it was typed
            # during mapping) or display name
            if not new_c['column_description']:
                if not new_c['display_name']:
                    new_c['column_description'] = new_c['column_name']
                else:
                    new_c['column_description'] = new_c['display_name']

            columns.append(new_c)

        # Sort by display name
        columns.sort(key=lambda col: col['display_name'].lower())

        return columns

    @staticmethod
    def retrieve_all(
        org_id: int,
        inventory_type: Optional[Literal['property', 'taxlot']] = None,
        only_used: bool = False,
        include_related: bool = True,
    ) -> list[dict]:
        """
        Retrieve all the columns for an organization. This method will query for all the columns in the
        database assigned to the organization. It will then go through and cleanup the names to ensure that
        there are no duplicates. The name column is used for uniquely labeling the columns for UI Grid purposes.

        :param org_id: Organization ID
        :param inventory_type: Inventory Type (property|taxlot) from the requester. This sets the related columns if requested.
        :param only_used: View only the used columns that exist in the Column's table
        :param include_related: Include related columns (e.g. if inventory type is Property, include Taxlot columns)
        """
        from seed.serializers.columns import ColumnSerializer

        # Grab all the columns out of the database for the organization that are assigned to a
        # table_name. Order extra_data last so that extra data duplicate-checking will happen after
        # processing standard columns
        columns_db = Column.objects.filter(organization_id=org_id).exclude(table_name='').exclude(
            table_name=None).order_by('is_extra_data', 'column_name')
        columns = []
        for c in columns_db:
            if c.column_name in Column.EXCLUDED_COLUMN_RETURN_FIELDS:
                continue

            # Eventually move this over to Column serializer directly
            new_c = ColumnSerializer(c).data

            new_c['sharedFieldType'] = new_c['shared_field_type']
            del new_c['shared_field_type']

            if (new_c['table_name'], new_c['column_name']) in Column.PINNED_COLUMNS:
                new_c['pinnedLeft'] = True

            # If no display name, use the column name (this is the display name as it was typed
            # during mapping)
            if not new_c['display_name']:
                new_c['display_name'] = new_c['column_name']

            # If no column_description, use the column name (this is the display name as it was typed
            # during mapping) or display name
            if not new_c['column_description']:
                if not new_c['display_name']:
                    new_c['column_description'] = new_c['column_name']
                else:
                    new_c['column_description'] = new_c['display_name']

            # Related fields
            new_c['related'] = False
            if inventory_type:
                new_c['related'] = not (inventory_type.lower() in new_c['table_name'].lower())
                if new_c['related']:
                    # if it is related then have the display name show the other table
                    new_c['display_name'] = new_c['display_name'] + ' (%s)' % INVENTORY_DISPLAY[
                        new_c['table_name']]

            include_column = True
            if only_used:
                # only add the column if it is in a ColumnMapping object
                include_column = include_column and ColumnMapping.objects.filter(column_mapped=c).exists()
            if not include_related:
                # only add the column if it is not a related column
                is_not_related = not new_c['related']
                include_column = include_column and is_not_related

            if include_column:
                columns.append(new_c)

        # import json
        # print(json.dumps(columns, indent=2))

        # validate that the field 'name' is unique.
        uniq = set()
        for c in columns:
            if (c['table_name'], c['column_name']) in uniq:
                raise Exception("Duplicate name '{}' found in columns".format(c['name']))
            else:
                uniq.add((c['table_name'], c['column_name']))

        return columns

    @staticmethod
    def retrieve_priorities(org_id):
        """
        Return the list of priorities for the columns. Result will be in the form of:

        .. code-block:: json

            {
                'PropertyState': {
                    'lot_number': 'Favor New',
                    'owner_address': 'Favor New',
                    'extra_data': {
                        'data_007': 'Favor New'
                    }
                'TaxLotState': {
                    'custom_id_1': 'Favor New',
                    'block_number': 'Favor New',
                    'extra_data': {
                        'data_008': 'Favor New'
                    }
            }

        :param org_id: organization with the columns
        :return: dict
        """
        columns = Column.retrieve_all(org_id, 'property', False)
        # The TaxLot and Property are not used in merging, they are just here to prevent errors
        priorities = {
            'PropertyState': {'extra_data': {}},
            'TaxLotState': {'extra_data': {}},
            'Property': {},
            'TaxLot': {}
        }
        for column in columns:
            tn = column['table_name']
            cn = column['column_name']
            if column['is_extra_data']:
                priorities[tn]['extra_data'][cn] = column.get('merge_protection', 'Favor New')
            else:
                priorities[tn][cn] = column.get('merge_protection', 'Favor New')

        return priorities

    @staticmethod
    def retrieve_all_by_tuple(org_id):
        """
        Return list of all columns for an organization as a tuple.

        .. code-block:: json

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
        for col in Column.retrieve_all(org_id, None, False):
            result.append((col['table_name'], col['column_name']))

        return result


def validate_model(sender, **kwargs):
    instance = kwargs['instance']
    if instance.is_extra_data and instance.is_matching_criteria:
        raise IntegrityError("Extra data columns can't be matching criteria.")

    if 'raw' in kwargs and not kwargs['raw']:
        instance.full_clean()


pre_save.connect(validate_model, sender=Column)
