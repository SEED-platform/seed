"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import copy
import csv
import locale
import logging
import os.path
from collections import OrderedDict
from datetime import datetime
from typing import Any, Callable, Literal, Optional

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, models, transaction
from django.db.models import Count, Q
from django.db.models.signals import pre_save
from django.utils.translation import gettext_lazy as _

from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.lib.superperms.orgs.models import OrganizationUser
from seed.models.column_mappings import ColumnMapping
from seed.models.models import Unit

INVENTORY_DISPLAY = {
    "PropertyState": "Property",
    "TaxLotState": "Tax Lot",
    "Property": "Property",
    "TaxLot": "Tax Lot",
}
_log = logging.getLogger(__name__)


class ColumnCastError(Exception):
    pass


# These fields are excluded from being returned to the front end via the API and the
# Column.retrieve_all method. Note that not all the endpoints are respecting this at the moment.
EXCLUDED_API_FIELDS = [
    "normalized_address",
]


class Column(models.Model):
    """The name of a column for a given organization."""

    SHARED_NONE = 0
    SHARED_PUBLIC = 1

    SHARED_FIELD_TYPES = ((SHARED_NONE, "None"), (SHARED_PUBLIC, "Public"))

    PINNED_COLUMNS = [("PropertyState", "pm_property_id"), ("TaxLotState", "jurisdiction_tax_lot_id")]

    # Do not return these columns to the front end -- when using the tax_lot_properties
    # get_related method.
    EXCLUDED_COLUMN_RETURN_FIELDS = [
        "hash_object",
        "normalized_address",
        # Records below are old and should not be used
        "source_eui_modeled_orig",
        "site_eui_orig",
        "occupied_floor_area_orig",
        "site_eui_weather_normalized_orig",
        "site_eui_modeled_orig",
        "source_eui_orig",
        "gross_floor_area_orig",
        "conditioned_floor_area_orig",
        "source_eui_weather_normalized_orig",
    ]

    QUANTITY_UNIT_COLUMNS = [
        ("PropertyState", "gross_floor_area"),
        ("PropertyState", "occupied_floor_area"),
        ("PropertyState", "conditioned_floor_area"),
        ("PropertyState", "site_eui"),
        ("PropertyState", "site_eui_modeled"),
        ("PropertyState", "site_eui_weather_normalized"),
        ("PropertyState", "source_eui"),
        ("PropertyState", "source_eui_modeled"),
        ("PropertyState", "source_eui_weather_normalized"),
        ("PropertyState", "total_ghg_emissions"),
        ("PropertyState", "total_marginal_ghg_emissions"),
        ("PropertyState", "total_ghg_emissions_intensity"),
        ("PropertyState", "total_marginal_ghg_emissions_intensity"),
        ("PropertyState", "water_use"),
        ("PropertyState", "indoor_water_use"),
        ("PropertyState", "outdoor_water_use"),
        ("PropertyState", "wui"),
        ("PropertyState", "indoor_wui"),
    ]

    COLUMN_MERGE_FAVOR_NEW = 0
    COLUMN_MERGE_FAVOR_EXISTING = 1
    COLUMN_MERGE_PROTECTION = [(COLUMN_MERGE_FAVOR_NEW, "Favor New"), (COLUMN_MERGE_FAVOR_EXISTING, "Favor Existing")]

    # These are the columns that are removed when looking to see if the records are the same
    COLUMN_EXCLUDE_FIELDS = [
        "bounding_box",
        "centroid",
        "created",
        "data_state",
        "derived_data",
        "extra_data",
        "geocoding_confidence",
        "id",
        "import_file",
        "long_lat",
        "merge_state",
        "raw_access_level_instance_error",
        "raw_access_level_instance_id",
        "source_type",
        "updated",
        *EXCLUDED_COLUMN_RETURN_FIELDS,
    ]

    # These are columns that you cannot rename fields to
    EXCLUDED_RENAME_TO_FIELDS = [
        "lot_number",
        "latitude",
        "longitude",
        "year_built",
        "property_footprint",
        "created",
        "updated",
        *COLUMN_EXCLUDE_FIELDS,
    ]

    # These are column names that you can't rename at all
    EXCLUDED_RENAME_FROM_FIELDS = [
        "lot_number",
        "year_built",
        "property_footprint",
        "taxlot_footprint",
        *COLUMN_EXCLUDE_FIELDS,
    ]

    # These are fields that should not be mapped to, ever. AKA Protected column fields
    # for either PropertyState or TaxLotState. They will not be shown in the mapping
    # suggestions.
    EXCLUDED_MAPPING_FIELDS = [
        "created",
        "extra_data",
        "lot_number",
        "normalized_address",
        "geocoded_address",
        "geocoded_postal_code",
        "geocoded_side_of_street",
        "geocoded_country",
        "geocoded_state",
        "geocoded_county",
        "geocoded_city",
        "geocoded_neighborhood",
        "updated",
    ]

    # These are columns that should not be offered as suggestions during mapping for
    # properties and tax lots
    UNMAPPABLE_PROPERTY_FIELDS = [
        "created",
        "geocoding_confidence",
        "lot_number",
        "updated",
    ]
    UNMAPPABLE_TAXLOT_FIELDS = [
        "created",
        "geocoding_confidence",
        "updated",
    ]

    INTERNAL_TYPE_TO_DATA_TYPE = {
        "FloatField": "double",  # yes, technically this is not the same, move along.
        "IntegerField": "integer",
        "CharField": "string",
        "TextField": "string",
        "DateField": "date",
        "DateTimeField": "datetime",
        "BooleanField": "boolean",
        "JSONField": "string",
        "PolygonField": "geometry",
        "PointField": "geometry",
    }

    DB_TYPES = {
        "number": "float",
        "float": "float",
        "integer": "integer",
        "string": "string",
        "geometry": "geometry",
        "datetime": "datetime",
        "date": "date",
        "boolean": "boolean",
        "area": "float",
        "eui": "float",
        "ghg": "float",
        "ghg_intensity": "float",
        "wui": "float",
        "water_use": "float",
    }

    DATA_TYPE_PARSERS: dict[str, Callable] = {
        "number": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "float": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "integer": lambda v: int(v.replace(",", "") if isinstance(v, str) else v),
        "string": str,
        "geometry": str,
        "datetime": datetime.fromisoformat,
        "date": lambda v: datetime.fromisoformat(v).date(),
        "boolean": lambda v: v.lower() == "true",
        "area": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "eui": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "ghg_intensity": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "ghg": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "wui": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
        "water_use": lambda v: float(v.replace(",", "") if isinstance(v, str) else v),
    }

    # These are the default columns (also known as the fields in the database)
    DATABASE_COLUMNS = [
        {
            "column_name": "pm_property_id",
            "table_name": "PropertyState",
            "display_name": "PM Property ID",
            "column_description": "PM Property ID",
            "data_type": "string",
        },
        {
            "column_name": "pm_parent_property_id",
            "table_name": "PropertyState",
            "display_name": "PM Parent Property ID",
            "column_description": "PM Parent Property ID",
            "data_type": "string",
        },
        {
            "column_name": "jurisdiction_tax_lot_id",
            "table_name": "TaxLotState",
            "display_name": "Jurisdiction Tax Lot ID",
            "column_description": "Jurisdiction Tax Lot ID",
            "data_type": "string",
        },
        {
            "column_name": "jurisdiction_property_id",
            "table_name": "PropertyState",
            "display_name": "Jurisdiction Property ID",
            "column_description": "Jurisdiction Property ID",
            "data_type": "string",
        },
        {
            "column_name": "ubid",
            "table_name": "TaxLotState",
            "display_name": "UBID",
            "column_description": "UBID",
            "data_type": "string",
        },
        {
            "column_name": "ubid",
            "table_name": "PropertyState",
            "display_name": "UBID",
            "column_description": "UBID",
            "data_type": "string",
        },
        {
            "column_name": "custom_id_1",
            "table_name": "PropertyState",
            "display_name": "Custom ID 1",
            "column_description": "Custom ID 1",
            "data_type": "string",
        },
        {
            "column_name": "custom_id_1",
            "table_name": "TaxLotState",
            "display_name": "Custom ID 1",
            "column_description": "Custom ID 1",
            "data_type": "string",
        },
        {
            "column_name": "audit_template_building_id",
            "table_name": "PropertyState",
            "display_name": "Audit Template Building ID",
            "column_description": "Audit Template Building ID",
            "data_type": "string",
        },
        {
            "column_name": "address_line_1",
            "table_name": "PropertyState",
            "display_name": "Address Line 1",
            "column_description": "Address Line 1",
            "data_type": "string",
        },
        {
            "column_name": "address_line_1",
            "table_name": "TaxLotState",
            "display_name": "Address Line 1",
            "column_description": "Address Line 1",
            "data_type": "string",
        },
        {
            "column_name": "address_line_2",
            "table_name": "PropertyState",
            "display_name": "Address Line 2",
            "column_description": "Address Line 2",
            "data_type": "string",
        },
        {
            "column_name": "address_line_2",
            "table_name": "TaxLotState",
            "display_name": "Address Line 2",
            "column_description": "Address Line 2",
            "data_type": "string",
        },
        {
            "column_name": "city",
            "table_name": "PropertyState",
            "display_name": "City",
            "column_description": "City",
            "data_type": "string",
        },
        {
            "column_name": "city",
            "table_name": "TaxLotState",
            "display_name": "City",
            "column_description": "City",
            "data_type": "string",
        },
        {
            "column_name": "state",
            "table_name": "PropertyState",
            "display_name": "State",
            "column_description": "State",
            "data_type": "string",
        },
        {
            "column_name": "state",
            "table_name": "TaxLotState",
            "display_name": "State",
            "column_description": "State",
            "data_type": "string",
        },
        {
            # This should never be mapped to!
            "column_name": "normalized_address",
            "table_name": "PropertyState",
            "display_name": "Normalized Address",
            "column_description": "Normalized Address",
            "data_type": "string",
        },
        {
            # This should never be mapped to!
            "column_name": "normalized_address",
            "table_name": "TaxLotState",
            "display_name": "Normalized Address",
            "column_description": "Normalized Address",
            "data_type": "string",
        },
        {
            "column_name": "postal_code",
            "table_name": "PropertyState",
            "display_name": "Postal Code",
            "column_description": "Postal Code",
            "data_type": "string",
        },
        {
            "column_name": "postal_code",
            "table_name": "TaxLotState",
            "display_name": "Postal Code",
            "column_description": "Postal Code",
            "data_type": "string",
        },
        {
            # This field should never be mapped to!
            "column_name": "lot_number",
            "table_name": "PropertyState",
            "display_name": "Associated Tax Lot ID",
            "column_description": "Associated Tax Lot ID",
            "data_type": "string",
        },
        {
            "column_name": "property_name",
            "table_name": "PropertyState",
            "display_name": "Property Name",
            "column_description": "Property Name",
            "data_type": "string",
        },
        {
            "column_name": "latitude",
            "table_name": "PropertyState",
            "display_name": "Latitude",
            "column_description": "Latitude",
            "data_type": "number",
        },
        {
            "column_name": "longitude",
            "table_name": "PropertyState",
            "display_name": "Longitude",
            "column_description": "Longitude",
            "data_type": "number",
        },
        {
            "column_name": "latitude",
            "table_name": "TaxLotState",
            "display_name": "Latitude",
            "column_description": "Latitude",
            "data_type": "number",
        },
        {
            "column_name": "longitude",
            "table_name": "TaxLotState",
            "display_name": "Longitude",
            "column_description": "Longitude",
            "data_type": "number",
        },
        {
            "column_name": "geocoding_confidence",
            "table_name": "PropertyState",
            "display_name": "Geocoding Confidence",
            "column_description": "Geocoding Confidence",
            "data_type": "string",
        },
        {
            "column_name": "geocoding_confidence",
            "table_name": "TaxLotState",
            "display_name": "Geocoding Confidence",
            "column_description": "Geocoding Confidence",
            "data_type": "string",
        },
        {
            "column_name": "property_footprint",
            "table_name": "PropertyState",
            "display_name": "Property Footprint",
            "column_description": "Property Footprint",
            "data_type": "geometry",
        },
        {
            "column_name": "taxlot_footprint",
            "table_name": "TaxLotState",
            "display_name": "Tax Lot Footprint",
            "column_description": "Tax Lot Footprint",
            "data_type": "geometry",
        },
        {
            "column_name": "updated",
            "table_name": "PropertyState",
            "display_name": "Updated",
            "column_description": "Updated",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "created",
            "table_name": "PropertyState",
            "display_name": "Created",
            "column_description": "Created",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "updated",
            "table_name": "TaxLotState",
            "display_name": "Updated",
            "column_description": "Updated",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "created",
            "table_name": "TaxLotState",
            "display_name": "Created",
            "column_description": "Created",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "gross_floor_area",
            "table_name": "PropertyState",
            "display_name": "Gross Floor Area",
            "column_description": "Gross Floor Area",
            "data_type": "area",
            # "type": "number",
        },
        {
            "column_name": "use_description",
            "table_name": "PropertyState",
            "display_name": "Use Description",
            "column_description": "Use Description",
            "data_type": "string",
        },
        {
            "column_name": "energy_score",
            "table_name": "PropertyState",
            "display_name": "ENERGY STAR Score",
            "column_description": "ENERGY STAR Score",
            "data_type": "integer",
            # "type": "number",
        },
        {
            "column_name": "property_notes",
            "table_name": "PropertyState",
            "display_name": "Property Notes",
            "column_description": "Property Notes",
            "data_type": "string",
        },
        {
            "column_name": "property_type",
            "table_name": "PropertyState",
            "display_name": "Property Type",
            "column_description": "Property Type",
            "data_type": "string",
        },
        {
            "column_name": "year_ending",
            "table_name": "PropertyState",
            "display_name": "Year Ending",
            "column_description": "Year Ending",
            "data_type": "date",
        },
        {
            "column_name": "owner",
            "table_name": "PropertyState",
            "display_name": "Owner",
            "column_description": "Owner",
            "data_type": "string",
        },
        {
            "column_name": "owner_email",
            "table_name": "PropertyState",
            "display_name": "Owner Email",
            "column_description": "Owner Email",
            "data_type": "string",
        },
        {
            "column_name": "owner_telephone",
            "table_name": "PropertyState",
            "display_name": "Owner Telephone",
            "column_description": "Owner Telephone",
            "data_type": "string",
        },
        {
            "column_name": "building_count",
            "table_name": "PropertyState",
            "display_name": "Building Count",
            "column_description": "Building Count",
            "data_type": "integer",
            # "type": "number",
        },
        {
            "column_name": "year_built",
            "table_name": "PropertyState",
            "display_name": "Year Built",
            "column_description": "Year Built",
            "data_type": "integer",
            # "type": "number",
        },
        {
            "column_name": "recent_sale_date",
            "table_name": "PropertyState",
            "display_name": "Recent Sale Date",
            "column_description": "Recent Sale Date",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "conditioned_floor_area",
            "table_name": "PropertyState",
            "display_name": "Conditioned Floor Area",
            "column_description": "Conditioned Floor Area",
            "data_type": "area",
            # "type": "number",
            # 'dbField': True,
        },
        {
            "column_name": "occupied_floor_area",
            "table_name": "PropertyState",
            "display_name": "Occupied Floor Area",
            "column_description": "Occupied Floor Area",
            "data_type": "area",
            # "type": "number",
        },
        {
            "column_name": "owner_address",
            "table_name": "PropertyState",
            "display_name": "Owner Address",
            "column_description": "Owner Address",
            "data_type": "string",
        },
        {
            "column_name": "owner_city_state",
            "table_name": "PropertyState",
            "display_name": "Owner City/State",
            "column_description": "Owner City/State",
            "data_type": "string",
        },
        {
            "column_name": "owner_postal_code",
            "table_name": "PropertyState",
            "display_name": "Owner Postal Code",
            "column_description": "Owner Postal Code",
            "data_type": "string",
        },
        {
            "column_name": "home_energy_score_id",
            "table_name": "PropertyState",
            "display_name": "Home Energy Score ID",
            "column_description": "Home Energy Score ID",
            "data_type": "string",
        },
        {
            "column_name": "generation_date",
            "table_name": "PropertyState",
            "display_name": "PM Generation Date",
            "column_description": "PM Generation Date",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "release_date",
            "table_name": "PropertyState",
            "display_name": "PM Release Date",
            "column_description": "PM Release Date",
            "data_type": "datetime",
            # 'type': 'date',
            # 'cellFilter': 'date:\'yyyy-MM-dd h:mm a\'',
        },
        {
            "column_name": "site_eui",
            "table_name": "PropertyState",
            "display_name": "Site EUI",
            "column_description": "Site EUI",
            "data_type": "eui",
            # "type": "number",
        },
        {
            "column_name": "site_eui_weather_normalized",
            "table_name": "PropertyState",
            "display_name": "Site EUI Weather Normalized",
            "column_description": "Site EUI Weather Normalized",
            "data_type": "eui",
            # "type": "number",
        },
        {
            "column_name": "site_eui_modeled",
            "table_name": "PropertyState",
            "display_name": "Site EUI Modeled",
            "column_description": "Site EUI Modeled",
            "data_type": "eui",
            # "type": "number",
        },
        {
            "column_name": "source_eui",
            "table_name": "PropertyState",
            "display_name": "Source EUI",
            "column_description": "Source EUI",
            "data_type": "eui",
            # "type": "number",
        },
        {
            "column_name": "source_eui_weather_normalized",
            "table_name": "PropertyState",
            "display_name": "Source EUI Weather Normalized",
            "column_description": "Source EUI Weather Normalized",
            "data_type": "eui",
            # "type": "number",
        },
        {
            "column_name": "source_eui_modeled",
            "table_name": "PropertyState",
            "display_name": "Source EUI Modeled",
            "column_description": "Source EUI Modeled",
            "data_type": "eui",
            # "type": "number",
        },
        {
            "column_name": "energy_alerts",
            "table_name": "PropertyState",
            "display_name": "Energy Alerts",
            "column_description": "Energy Alerts",
            "data_type": "string",
        },
        {
            "column_name": "space_alerts",
            "table_name": "PropertyState",
            "display_name": "Space Alerts",
            "column_description": "Space Alerts",
            "data_type": "string",
        },
        {
            "column_name": "building_certification",
            "table_name": "PropertyState",
            "display_name": "Building Certification",
            "column_description": "Building Certification",
            "data_type": "string",
        },
        {
            "column_name": "number_properties",
            "table_name": "TaxLotState",
            "display_name": "Number Properties",
            "column_description": "Number Properties",
            "data_type": "integer",
            # "type": "number",
        },
        {
            "column_name": "block_number",
            "table_name": "TaxLotState",
            "display_name": "Block Number",
            "column_description": "Block Number",
            "data_type": "string",
        },
        {
            "column_name": "district",
            "table_name": "TaxLotState",
            "display_name": "District",
            "column_description": "District",
            "data_type": "string",
        },
        {
            "column_name": "egrid_subregion_code",
            "table_name": "PropertyState",
            "display_name": "eGRID Subregion Code",
            "column_description": "eGRID Subregion Code",
            "data_type": "string",
        },
        {
            "column_name": "total_ghg_emissions",
            "table_name": "PropertyState",
            "display_name": "Total GHG Emissions",
            "column_description": "Total GHG Emissions",
            "data_type": "ghg",
        },
        {
            "column_name": "total_marginal_ghg_emissions",
            "table_name": "PropertyState",
            "display_name": "Total Marginal GHG Emissions",
            "column_description": "Total Marginal GHG Emissions",
            "data_type": "ghg",
        },
        {
            "column_name": "total_ghg_emissions_intensity",
            "table_name": "PropertyState",
            "display_name": "Total GHG Emissions Intensity",
            "column_description": "Total GHG Emissions Intensity",
            "data_type": "ghg_intensity",
        },
        {
            "column_name": "total_marginal_ghg_emissions_intensity",
            "table_name": "PropertyState",
            "display_name": "Total Marginal GHG Emissions Intensity",
            "column_description": "Total Marginal GHG Emissions Intensity",
            "data_type": "ghg_intensity",
        },
        {
            "column_name": "property_timezone",
            "table_name": "PropertyState",
            "display_name": "Property Time Zone",
            "column_description": "Time zone of the property",
            "data_type": "string",
        },
        {
            "column_name": "water_use",
            "table_name": "PropertyState",
            "display_name": "Water Use",
            "column_description": "Water Use (All Water Sources)",
            "data_type": "water_use",
        },
        {
            "column_name": "indoor_water_use",
            "table_name": "PropertyState",
            "display_name": "Indoor Water Use",
            "column_description": "Indoor Water Use (All Water Sources)",
            "data_type": "water_use",
        },
        {
            "column_name": "outdoor_water_use",
            "table_name": "PropertyState",
            "display_name": "Outdoor Water Use",
            "column_description": "Outdoor Water Use (All Water Sources)",
            "data_type": "water_use",
        },
        {
            "column_name": "wui",
            "table_name": "PropertyState",
            "display_name": "WUI",
            "column_description": "Water Use Intensity (All Water Sources)",
            "data_type": "wui",
        },
        {
            "column_name": "indoor_wui",
            "table_name": "PropertyState",
            "display_name": "Indoor WUI",
            "column_description": "Indoor Water Use Intensity (All Water Sources)",
            "data_type": "wui",
        },
    ]
    organization = models.ForeignKey(SuperOrganization, on_delete=models.CASCADE, blank=True, null=True)
    column_name = models.CharField(max_length=512, db_index=True)
    # name of the table which the column name applies, if the column name
    # is a db field. Options now are only PropertyState and TaxLotState
    table_name = models.CharField(max_length=512, blank=True, db_index=True)

    display_name = models.CharField(max_length=512, blank=True)
    column_description = models.TextField(max_length=1000, blank=True, default=None)
    data_type = models.CharField(max_length=64, default="None")

    # Add created/modified timestamps
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, blank=True, null=True)
    is_extra_data = models.BooleanField(default=False)
    is_matching_criteria = models.BooleanField(default=False)
    is_option_for_reports_x_axis = models.BooleanField(default=False)
    is_option_for_reports_y_axis = models.BooleanField(default=False)
    is_excluded_from_hash = models.BooleanField(default=False)

    import_file = models.ForeignKey("data_importer.ImportFile", on_delete=models.CASCADE, blank=True, null=True)
    # TODO: units_pint should be renamed to `from_units` as this is the unit of the incoming data in pint format
    units_pint = models.CharField(max_length=64, blank=True, null=True)

    # 0 is deactivated. Order used to construct full address.
    geocoding_order = models.IntegerField(default=0, blank=False)

    shared_field_type = models.IntegerField(choices=SHARED_FIELD_TYPES, default=SHARED_NONE)

    # By default, when two records are merge the new data will take precedence over the existing
    # data, however, the user can override this on a column-by-column basis.
    merge_protection = models.IntegerField(choices=COLUMN_MERGE_PROTECTION, default=COLUMN_MERGE_FAVOR_NEW)

    recognize_empty = models.BooleanField(default=False)

    comstock_mapping = models.CharField(max_length=64, null=True, blank=True, default=None)
    derived_column = models.OneToOneField("DerivedColumn", on_delete=models.CASCADE, null=True, blank=True)
    is_updating = models.BooleanField(null=False, default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "comstock_mapping"], name="unique_comstock_mapping"),
            # create a name constraint on the column. The name must be unique across the organization,
            # table_name (property or tax lot), if it is extra_data. Note that this may require some
            # database cleanup because older organizations might have imported data before the `units_pint`
            # column existed and there will be duplicates.
            models.UniqueConstraint(fields=["organization", "column_name", "table_name", "is_extra_data"], name="unique_column_name"),
        ]

    def __str__(self):
        return f"{self.pk} - {self.table_name}:{self.column_name}"

    def clean(self):
        if self.derived_column:
            return
        # Don't allow Columns that are not extra_data and not a field in the database
        if (not self.is_extra_data) and self.table_name:
            # if it isn't extra data and the table_name IS set, then it must be part of the database fields
            found = False
            for c in Column.DATABASE_COLUMNS:
                if self.table_name == c["table_name"] and self.column_name == c["column_name"]:
                    found = True

            if not found:
                raise ValidationError(
                    {
                        "is_extra_data": _(
                            "Column '%s':'%s' is not a field in the database and not marked as extra data. Mark as extra data to save column."
                        )
                        % (self.table_name, self.column_name)
                    }
                )

    def cast(self, value: Any) -> Any:
        """Cast the value to the correct type for the column.

        Args:
            value (Any): Value to cast, typically a string.
        """
        return Column.cast_column_value(self.data_type, value)

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

        STR_TO_CLASS = {"TaxLotState": TaxLotState, "PropertyState": PropertyState}

        def _serialize_for_extra_data(column_value):
            if isinstance(column_value, (date_type, datetime_type)):
                return column_value.isoformat()
            elif isinstance(column_value, ureg.Quantity):
                return column_value.magnitude
            else:
                return column_value

        # restricted columns to rename to or from
        if new_column_name in self.EXCLUDED_RENAME_TO_FIELDS:
            return [False, f"Column name '{new_column_name}' is a reserved name. Choose another."]

        # Do not allow moving data out of the property based columns
        if self.column_name in self.EXCLUDED_RENAME_FROM_FIELDS or self.table_name in {"Property", "TaxLot"}:
            return [False, f"Can't move data out of reserved column '{self.column_name}'"]

        try:
            with transaction.atomic():
                # check if the new_column already exists
                new_column = Column.objects.filter(table_name=self.table_name, column_name=new_column_name, organization=self.organization)
                if len(new_column) > 0:
                    if not force:
                        return [False, "New column already exists, specify overwrite data if desired"]

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
                        merge_protection=self.merge_protection,
                    )

                # go through the data and move it to the new field. I'm not sure yet on how long this is
                # going to take to run, so we may have to move this to a background task
                orig_data = STR_TO_CLASS[self.table_name].objects.filter(organization=self.organization, data_state=DATA_STATE_MATCHING)
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
                elif self.is_extra_data:
                    for datum in orig_data:
                        setattr(datum, new_column.column_name, datum.extra_data.get(self.column_name, None))
                        datum.extra_data.pop(self.column_name, None)
                        datum.save()
                else:
                    for datum in orig_data:
                        setattr(datum, new_column.column_name, getattr(datum, self.column_name))
                        setattr(datum, self.column_name, None)
                        datum.save()
        except (ValidationError, DataError, ValueError):
            return [
                False,
                "The column data aren't formatted properly for the new column due to type constraints (e.g., Datetime, Quantities, etc.).",
            ]
        except DimensionalityError:
            return [
                False,
                "The column data can't be converted to the new column due to conversion constraints (e.g., converting square feet to kBtu etc.).",
            ]

        # Return true if this operation was successful
        return [True, "Successfully renamed column and moved data"]

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
            with open(filename, newline=None, encoding=locale.getpreferredencoding(False)) as csvfile:
                for row in csv.reader(csvfile):
                    data = {
                        "from_field": row[0],
                        "to_table_name": row[1],
                        "to_field": row[2],
                        "to_display_name": row[3],
                        "to_data_type": row[4],
                        "to_unit_type": row[5],
                    }
                    mappings.append(data)
        else:
            raise Exception(f"Mapping file does not exist: {filename}")

        if len(mappings) == 0:
            raise Exception(f"No mappings in file: {filename}")
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
                        'to_data_type': 'string', # an internal data type mapping
                    }
                ]
        """

        # initialize a cache to store the mappings
        cache_column_mapping = []
        # Take the existing object and return the same object with the db column objects added to
        # the dictionary (to_column_object and from_column_object)
        mappings = Column._column_fields_to_columns(mappings, organization, user)
        for mapping in mappings:
            if isinstance(mapping, dict):
                try:
                    column_mapping, _ = ColumnMapping.objects.get_or_create(
                        super_organization=organization,
                        column_raw__in=mapping["from_column_object"],
                    )
                except ColumnMapping.MultipleObjectsReturned:
                    _log.debug("ColumnMapping.MultipleObjectsReturned in create_mappings")
                    # handle the special edge-case where remove dupes does not get
                    # called by ``get_or_create``
                    ColumnMapping.objects.filter(
                        super_organization=organization,
                        column_raw__in=mapping["from_column_object"],
                    ).delete()

                    column_mapping, _ = ColumnMapping.objects.get_or_create(
                        super_organization=organization,
                        column_raw__in=mapping["from_column_object"],
                    )

                # Clear out the column_raw and column mapped relationships. -- NL really? history?
                column_mapping.column_raw.clear()
                column_mapping.column_mapped.clear()

                # Add all that we got back from the interface back in the M2M rel.
                [column_mapping.column_raw.add(raw_col) for raw_col in mapping["from_column_object"]]
                if mapping["to_column_object"] is not None:
                    [column_mapping.column_mapped.add(dest_col) for dest_col in mapping["to_column_object"]]

                column_mapping.user = user
                column_mapping.save()
                cache_column_mapping.append(
                    {
                        "from_field": mapping["from_field"],
                        "from_units": mapping.get("from_units"),
                        "to_field": mapping["to_field"],
                        "to_table_name": mapping["to_table_name"],
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
    def _column_fields_to_columns(fields, organization, user):
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
        # Container to store the dicts with the Column object
        new_data = []
        org_user = OrganizationUser.objects.get(organization=organization, user=user)
        is_root_user = org_user.access_level_instance == organization.root

        for field in fields:
            new_field = field
            is_ah_data = any(field["to_field"] == name for name in organization.access_level_names)
            is_extra_data = not any(
                field["to_table_name"] == c["table_name"] and field["to_field"] == c["column_name"] for c in Column.DATABASE_COLUMNS
            )

            to_col_params = {
                "organization": organization,
                "column_name": field["to_field"],
                "table_name": "" if is_ah_data else field["to_table_name"],
                "is_extra_data": is_extra_data,
            }
            # Only compare against data type if it is provided && the column is an extra data column
            if ("to_data_type" in field) and (is_extra_data):
                to_col_params["data_type"] = field["to_data_type"]

            if is_root_user or is_ah_data:
                to_org_col, _ = Column.objects.get_or_create(**to_col_params)
            else:
                try:
                    to_org_col = Column.objects.get(**to_col_params)
                except Column.DoesNotExist:
                    raise PermissionError(f"user does not have permission to create column {field['to_field']}")

            # the from column is the field in the import file, thus the table_name needs to be
            # blank. Eventually need to handle passing in import_file_id
            from_org_col, _ = Column.objects.update_or_create(
                organization=organization,
                table_name="",
                column_name=field["from_field"],
                is_extra_data=False,  # Column objects representing raw/header rows are NEVER extra data
                defaults={"units_pint": field.get("from_units", None)},
            )

            new_field["to_column_object"] = [to_org_col]
            new_field["from_column_object"] = [from_org_col]
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
            for i in range(5):
                while True:
                    try:
                        Column.objects.get_or_create(
                            table_name=model_obj.__class__.__name__,
                            column_name=key[:511],
                            is_extra_data=is_extra_data,
                            organization=model_obj.organization,
                        )
                    except Column.MultipleObjectsReturned:
                        _log.debug(f"Column.MultipleObjectsReturned for {key[:511]} in save_column_names")

                        columns = Column.objects.filter(
                            table_name=model_obj.__class__.__name__,
                            column_name=key[:511],
                            is_extra_data=is_extra_data,
                            organization=model_obj.organization,
                        )
                        for c in columns:
                            if not ColumnMapping.objects.filter(Q(column_raw=c) | Q(column_mapped=c)).exists():
                                _log.debug(f"Deleting column object {c.column_name}")
                                c.delete()

                        # Check if there are more than one column still
                        if (
                            Column.objects.filter(
                                table_name=model_obj.__class__.__name__,
                                column_name=key[:511],
                                is_extra_data=is_extra_data,
                                organization=model_obj.organization,
                            ).count()
                            > 1
                        ):
                            raise Exception(f"Could not fix duplicate columns for {key}. Contact dev team")

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
    def cast_column_value(column_data_type: str, value: Any, allow_none: bool = True) -> Any:
        """cast a single value from the column data type

        Args:
            column_data_type (str): The data type as defined in the column object
            value (Any): value to cast. Note the value may already be cast correctly.

        Raises:
            Exception: CastException if the value cannot be cast to the correct type

        Returns:
            Any: Resulting casted value
        """
        if value is None:
            if allow_none:
                return None
            else:
                raise ColumnCastError("Datum is None and allow_none is False.")

        parser = Column.DATA_TYPE_PARSERS.get(column_data_type, str)
        try:
            return parser(value)
        except Exception:
            raise ColumnCastError(f'Invalid data type for "{column_data_type}". Expected a valid "{column_data_type}" value.')

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

        types = OrderedDict()
        for c in columns:
            try:
                types[c["column_name"]] = Column.DB_TYPES[c["data_type"]]
            except KeyError:
                _log.error(f"could not find data_type for {c}")
                types[c["column_name"]] = ""

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
            set(
                Column.objects.filter(organization_id=org_id, is_extra_data=False)
                .order_by("column_name")
                .exclude(table_name="")
                .exclude(table_name=None)
                .values_list("column_name", flat=True)
            )
        )

        return result

    @staticmethod
    def retrieve_db_field_table_and_names_from_db_tables():
        """
        Similar to keys, except it returns a list of tuples of the columns that are in the database

        .. code-block:: python

            [
                ("PropertyState", "address_line_1"),
                ("PropertyState", "address_line_2"),
                ("PropertyState", "building_certification"),
                ("PropertyState", "building_count"),
                ("TaxLotState", "address_line_1"),
                ("TaxLotState", "address_line_2"),
                ("TaxLotState", "block_number"),
                ("TaxLotState", "city"),
                ("TaxLotState", "jurisdiction_tax_lot_id"),
            ]

        :return:list of tuples
        """
        result = set()
        for d in Column.retrieve_db_fields_from_db_tables():
            result.add((d["table_name"], d["column_name"]))

        return sorted(result)

    @staticmethod
    def retrieve_db_field_name_for_hash_comparison(inventory_type, organization_id):
        """
        Names only of the columns in the database (fields only, not extra data), independent of inventory type.
        These fields are used for generating an MD5 hash to quickly check if the data are the same across
        multiple records. Note that this ignores extra_data. The result is a superset of all the fields that are used
        in the database across all of the inventory types of interest.

        :return: list, names of columns, independent of inventory type.
        """
        excluded_columns = (
            list(
                Column.objects.filter(
                    is_excluded_from_hash=True,
                    table_name=inventory_type.__name__,
                    organization_id=organization_id,
                ).values_list("column_name", flat=True)
            )
            if (inventory_type.__name__ in ("PropertyState", "TaxLotState") and organization_id)
            else []
        )
        filter_fields_names = [
            f.name
            for f in inventory_type._meta.fields
            if (
                (f.get_internal_type() != "ForeignKey")
                and (f.name not in Column.COLUMN_EXCLUDE_FIELDS)
                and (f.name not in excluded_columns)
            )
        ]

        return sorted(set(filter_fields_names))

    @staticmethod
    def retrieve_db_fields_from_db_tables():
        """
        Return the list of database fields that are in the models. This is independent of what are in the
        Columns table.

        :return:
        """
        all_columns = []
        for f in apps.get_model("seed", "PropertyState")._meta.fields + apps.get_model("seed", "TaxLotState")._meta.fields:
            # this remove import_file and others
            if f.get_internal_type() == "ForeignKey":
                continue

            if f.name not in Column.COLUMN_EXCLUDE_FIELDS:
                dt = (f.get_internal_type() if f.get_internal_type else "string",)
                dt = Column.INTERNAL_TYPE_TO_DATA_TYPE[dt[0]]
                all_columns.append(
                    {
                        "table_name": f.model.__name__,
                        "column_name": f.name,
                        "data_type": dt,
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

        columns_db = Column.objects.filter(organization_id=org_id).exclude(table_name="").exclude(table_name=None)
        columns = []
        for c in columns_db:
            if c.column_name in Column.COLUMN_EXCLUDE_FIELDS or c.column_name in Column.EXCLUDED_MAPPING_FIELDS:
                continue

            # Eventually move this over to Column serializer directly
            new_c = ColumnSerializer(c).data

            if inventory_type:
                related = inventory_type.lower() not in new_c["table_name"].lower()
                if related:
                    continue
                if (inventory_type == "property" and c.column_name in Column.UNMAPPABLE_PROPERTY_FIELDS) or (
                    inventory_type == "taxlot" and c.column_name in Column.UNMAPPABLE_TAXLOT_FIELDS
                ):
                    continue

            new_c["sharedFieldType"] = new_c["shared_field_type"]
            del new_c["shared_field_type"]

            if (new_c["table_name"], new_c["column_name"]) in Column.PINNED_COLUMNS:
                new_c["pinnedLeft"] = True

            # If no display name, use the column name (this is the display name as it was typed
            # during mapping)
            if not new_c["display_name"]:
                new_c["display_name"] = new_c["column_name"]

            # If no column_description, use the column name (this is the display name as it was typed
            # during mapping) or display name
            if not new_c["column_description"]:
                if not new_c["display_name"]:
                    new_c["column_description"] = new_c["column_name"]
                else:
                    new_c["column_description"] = new_c["display_name"]

            columns.append(new_c)

        # Sort by display name
        columns.sort(key=lambda col: col["display_name"].lower())

        # Remove derived columns from mappable columns
        columns = [col for col in columns if not col["derived_column"]]

        return columns

    @staticmethod
    def retrieve_all(
        org_id: int,
        inventory_type: Optional[Literal["property", "taxlot"]] = None,
        only_used: bool = False,
        include_related: bool = True,
        exclude_derived: bool = False,
        column_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """
        Retrieve all the columns for an organization. This method will query for all the columns in the
        database assigned to the organization. It will then go through and cleanup the names to ensure that
        there are no duplicates. The name column is used for uniquely labeling the columns for UI Grid purposes.

        :param org_id: Organization ID
        :param inventory_type: Inventory Type (property|taxlot) from the requester. This sets the related columns if requested.
        :param only_used: View only the used columns that exist in the Column's table
        :param include_related: Include related columns (e.g., if inventory type is Property, include Taxlot columns)
        :param exclude_derived: Exclude derived columns.
        :param column_ids: List of Column ids.
        """
        from seed.serializers.columns import ColumnSerializer

        # Grab all the columns out of the database for the organization that are assigned to a
        # table_name. Order extra_data last so that extra data duplicate-checking will happen after
        # processing standard columns
        if column_ids:
            column_query = Column.objects.filter(organization_id=org_id, id__in=column_ids).exclude(table_name="").exclude(table_name=None)
        else:
            column_query = Column.objects.filter(organization_id=org_id).exclude(table_name="").exclude(table_name=None)
        if exclude_derived:
            column_query = column_query.exclude(derived_column__isnull=False)
        columns_db = column_query.order_by("is_extra_data", "column_name")
        columns = []
        # Eventually move all this over to Column serializer directly
        for c in ColumnSerializer(columns_db, many=True).data:
            if c["column_name"] in Column.EXCLUDED_COLUMN_RETURN_FIELDS:
                continue

            c["sharedFieldType"] = c["shared_field_type"]
            del c["shared_field_type"]

            if (c["table_name"], c["column_name"]) in Column.PINNED_COLUMNS:
                c["pinnedLeft"] = True

            # If no display name, use the column name (this is the display name as it was typed
            # during mapping)
            if not c["display_name"]:
                c["display_name"] = c["column_name"]

            # If no column_description, use the column name (this is the display name as it was typed
            # during mapping) or display name
            if not c["column_description"]:
                if not c["display_name"]:
                    c["column_description"] = c["column_name"]
                else:
                    c["column_description"] = c["display_name"]

            # Related fields
            c["related"] = False
            if inventory_type:
                c["related"] = inventory_type.lower() not in c["table_name"].lower()
                if c["related"]:
                    # if it is related then have the display name show the other table
                    c["display_name"] = f"{c['display_name']} ({INVENTORY_DISPLAY[c['table_name']]})"

            include_column = True
            if only_used:
                # only add the column if it is in a ColumnMapping object
                include_column = include_column and ColumnMapping.objects.filter(column_mapped=c["id"]).exists()
            if not include_related:
                # only add the column if it is not a related column
                is_not_related = not c["related"]
                include_column = include_column and is_not_related

            if include_column:
                columns.append(c)

        # validate that the field 'name' is unique.
        uniq = set()
        for c in columns:
            if (c["table_name"], c["column_name"]) in uniq:
                raise Exception(f"Duplicate name '{c['name']}' found in columns")
            else:
                uniq.add((c["table_name"], c["column_name"]))

        return columns

    @staticmethod
    def retrieve_priorities(org_id):
        """
        Return the list of priorities for the columns. Result will be in the form of:

        .. code-block:: python

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
        columns = Column.retrieve_all(org_id, "property", False)
        # The TaxLot and Property are not used in merging, they are just here to prevent errors
        priorities = {"PropertyState": {"extra_data": {}}, "TaxLotState": {"extra_data": {}}, "Property": {}, "TaxLot": {}}
        for column in columns:
            tn = column["table_name"]
            cn = column["column_name"]
            if column["is_extra_data"]:
                priorities[tn]["extra_data"][cn] = column.get("merge_protection", "Favor New")
            else:
                priorities[tn][cn] = column.get("merge_protection", "Favor New")

        return priorities

    @staticmethod
    def retrieve_all_by_tuple(org_id):
        """
        Return list of all columns for an organization as a tuple.

        .. code-block:: python

            [
                ("PropertyState", "address_line_1"),
                ("PropertyState", "address_line_2"),
                ("PropertyState", "building_certification"),
                ("PropertyState", "building_count"),
                ("TaxLotState", "address_line_1"),
                ("TaxLotState", "address_line_2"),
                ("TaxLotState", "block_number"),
                ("TaxLotState", "city"),
                ("TaxLotState", "jurisdiction_tax_lot_id"),
            ]

        :param org_id: int, Organization ID
        :return: list of tuples
        """
        result = []
        for col in Column.retrieve_all(org_id, None, False):
            result.append((col["table_name"], col["column_name"]))

        return result

    @staticmethod
    def get_num_of_nonnulls_by_column_name(state_ids, inventory_class, columns):
        states = inventory_class.objects.filter(id__in=state_ids)

        # init dicts
        num_of_nonnulls_by_column_name = {c.column_name: 0 for c in columns}
        canonical_columns = [c.column_name for c in columns if not c.is_extra_data]

        # add non-null counts for extra_data columns
        with connection.cursor() as cursor:
            table_name = "seed_propertystate" if inventory_class.__name__ == "PropertyState" else "seed_taxlotstate"
            non_null_extra_data_counts_query = (
                f"SELECT key, COUNT(*)\n"
                f"FROM {table_name}, LATERAL JSONB_EACH_TEXT(extra_data) AS each_entry(key, value)\n"
                f"WHERE id IN ({', '.join(map(str, state_ids))})\n"
                f"  AND value IS NOT NULL\n"
                f"GROUP BY key;"
            )
            cursor.execute(non_null_extra_data_counts_query)
            extra_data_counts = dict(cursor.fetchall())
            num_of_nonnulls_by_column_name.update(extra_data_counts)

        # add non-null counts for derived_data columns
        with connection.cursor() as cursor:
            table_name = "seed_propertystate" if inventory_class.__name__ == "PropertyState" else "seed_taxlotstate"
            non_null_derived_data_counts_query = (
                f"SELECT key, COUNT(*)\n"
                f"FROM {table_name}, LATERAL JSONB_EACH_TEXT(derived_data) AS each_entry(key, value)\n"
                f"WHERE id IN ({', '.join(map(str, state_ids))})\n"
                f"  AND value IS NOT NULL\n"
                f"GROUP BY key;"
            )
            cursor.execute(non_null_derived_data_counts_query)
            derived_data_counts = dict(cursor.fetchall())
            num_of_nonnulls_by_column_name.update(derived_data_counts)

        # add non-null counts for canonical columns
        canonical_counts = states.aggregate(**{col: Count(col) for col in canonical_columns})
        num_of_nonnulls_by_column_name.update(canonical_counts)

        return num_of_nonnulls_by_column_name


def validate_model(sender, **kwargs):
    instance = kwargs["instance"]
    if instance.is_extra_data and instance.is_matching_criteria:
        raise IntegrityError("Extra data columns can't be matching criteria.")

    if "raw" in kwargs and not kwargs["raw"]:
        instance.full_clean()

    if (
        instance.display_name is not None
        and instance.organization is not None
        and instance.display_name in instance.organization.access_level_names
    ):
        raise IntegrityError("This display name is already an access level name and cannot be used.")

    if instance.organization_id:
        org = SuperOrganization.objects.get(pk=instance.organization_id)
        if instance.display_name in org.access_level_names:
            raise ValidationError("This display name is an organization access level name.")


pre_save.connect(validate_model, sender=Column)
