# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# These are fields that are ignored when using methods that automatically determine names and
# cloning records
EXCLUDE_FIELDS = [
    'best_guess_canonical_building',
    'best_guess_confidence',
    'canonical_building',
    'canonical_for_ds',
    'children',
    'confidence',
    'created',
    'data_state',
    'duplicate',
    'extra_data',
    'id',
    # 'import_file',  # NEED import_file to copy over when we are merging records, leave it in for now.
    'last_modified_by',
    'match_type',
    'merge_state',
    'modified',
    'organization',
    'parents',
    'pk',
    'seed_org',
    'source_type',
    'super_organization',
]

META_FIELDS = [
    'best_guess_canonical_building',
    'best_guess_confidence',
    'canonical_for_ds',
    'confidence',
    'match_type',
    'source_type',
]

ASSESSOR_FIELDS = [
    {
        "title": "PM Property ID",
        "sort_column": "pm_property_id",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False,
        "static": False,
        "link": True
    },
    {
        "title": "Tax Lot ID",
        "sort_column": "tax_lot_id",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False,
        "static": False,
        "link": True
    },
    {
        "title": "Custom ID 1",
        "sort_column": "custom_id_1",
        "class": "is_aligned_right whitespace",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False,
        "static": False,
        "link": True
    },
    {
        "title": "Property Name",
        "sort_column": "property_name",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Address Line 1",
        "sort_column": "address_line_1",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Address Line 2",
        "sort_column": "address_line_2",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "County/District/Ward/Borough",
        "sort_column": "district",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Lot Number",
        "sort_column": "lot_number",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Block Number",
        "sort_column": "block_number",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "City",
        "sort_column": "city",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "State Province",
        "sort_column": "state_province",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Postal Code",
        "sort_column": "postal_code",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Year Built",
        "sort_column": "year_built",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "number",
        "min": "year_built__gte",
        "max": "year_built__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Use Description",
        "sort_column": "use_description",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Building Count",
        "sort_column": "building_count",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "number",
        "min": "building_count__gte",
        "max": "building_count__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Property Notes",
        "sort_column": "property_notes",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Property Type",
        "sort_column": "property_type",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Recent Sale Date",
        "sort_column": "recent_sale_date",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "recent_sale_date__gte",
        "max": "recent_sale_date__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Owner",
        "sort_column": "owner",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "checked": False
    },
    {
        "title": "Owner Address",
        "sort_column": "owner_address",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "checked": False
    },
    {
        "title": "Owner City",
        "sort_column": "owner_city_state",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "checked": False
    },
    {
        "title": "Owner Postal Code",
        "sort_column": "owner_postal_code",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "checked": False
    },
    {
        "title": "Owner Email",
        "sort_column": "owner_email",
        "class": "",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "checked": False
    },
    {
        "title": "Owner Telephone",
        "sort_column": "owner_telephone",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "string",
        "field_type": "contact_information",
        "checked": False
    },
    {
        "title": "Gross Floor Area",
        "sort_column": "gross_floor_area",
        "subtitle": u"ft" + u"\u00B2",
        "class": "is_aligned_right",
        "type": "floor_area",
        "min": "gross_floor_area__gte",
        "max": "gross_floor_area__lte",
        "field_type": "assessor",
        "checked": False
    },
    {
        "title": "Energy Star Score",
        "sort_column": "energy_score",
        "class": "is_aligned_right",
        "type": "number",
        "min": "energy_score__gte",
        "max": "energy_score__lte",
        "field_type": "pm",
        "checked": False
    },
    {
        "title": "Site EUI",
        "sort_column": "site_eui",
        "class": "is_aligned_right",
        "type": "number",
        "min": "site_eui__gte",
        "max": "site_eui__lte",
        "field_type": "pm",
        "checked": False
    },
    {
        "title": "Generation Date",
        "sort_column": "generation_date",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "generation_date__gte",
        "max": "generation_date__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Release Date",
        "sort_column": "release_date",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "release_date__gte",
        "max": "release_date__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Year Ending",
        "sort_column": "year_ending",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "year_ending__gte",
        "max": "year_ending__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Creation Date",
        "sort_column": "created",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "created__gte",
        "max": "created__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Modified Date",
        "sort_column": "modified",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Conditioned Floor Area",
        "sort_column": "conditioned_floor_area",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Occupied Floor Area",
        "sort_column": "occupied_floor_area",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Site EUI Weather Normalized",
        "sort_column": "site_eui_weather_normalized",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Source EUI",
        "sort_column": "source_eui",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Source EUI Weather Normalized",
        "sort_column": "source_eui_weather_normalized",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Building Certification",
        "sort_column": "building_certification",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Energy Alerts",
        "sort_column": "energy_alerts",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    },
    {
        "title": "Space Alerts",
        "sort_column": "space_alerts",
        "class": "is_aligned_right",
        "title_class": "",
        "type": "date",
        "min": "modified__gte",
        "max": "modified__lte",
        "field_type": "building_information",
        "checked": False
    }
]

ASSESSOR_FIELDS_BY_COLUMN = {field['sort_column']: field
                             for field in ASSESSOR_FIELDS}

# TODO: Merge this with other schemas.
# https://github.com/SEED-platform/seed/blob/d2bfe96e7503f670300448d5967a2bd6d5863634/seed/lib/mcm/data/SEED/seed.py
# https://github.com/SEED-platform/seed/blob/41c104cd105161c949e9cb379aac946ea9202c74/seed/lib/mappings/mapping_data.py  # noqa
VIEW_COLUMNS_PROPERTY = [
    {
        'name': 'pm_property_id',
        'table': 'PropertyState',
        'displayName': 'PM Property ID',
        'type': 'number',
        'pinIfNative': True,
    }, {
        'name': 'pm_parent_property_id',
        'table': 'PropertyState',
        'displayName': 'PM Parent Property ID',
        'type': 'numberStr',
    }, {
        'name': 'jurisdiction_tax_lot_id',
        'table': 'TaxLotState',
        'displayName': 'Jurisdiction Tax Lot ID',
        'type': 'numberStr',
        'pinIfNative': True,
    }, {
        'name': 'jurisdiction_property_id',
        'table': 'PropertyState',
        'displayName': 'Jurisdiction Property ID',
        'type': 'numberStr',
    }, {
        'name': 'custom_id_1',
        'table': 'PropertyState',
        'displayName': 'Custom ID 1 (Property)',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'custom_id_1',
        'table': 'TaxLotState',
        'displayName': 'Custom ID 1 (Tax Lot)',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'address_line_1',
        'table': 'PropertyState',
        'displayName': 'Address Line 1 (Property)',
        'type': 'numberStr',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'address_line_1',
        'table': 'TaxLotState',
        'displayName': 'Address Line 1 (Tax Lot)',
        'type': 'numberStr',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'address_line_2',
        'table': 'PropertyState',
        'displayName': 'Address Line 2 (Property)',
        'type': 'numberStr',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'address_line_2',
        'table': 'TaxLotState',
        'displayName': 'Address Line 2 (Tax Lot)',
        'type': 'numberStr',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'city',
        'table': 'PropertyState',
        'displayName': 'City (Property)',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'city',
        'table': 'TaxLotState',
        'displayName': 'City (Tax Lot)',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'state',
        'table': 'PropertyState',
        'displayName': 'State (Property)',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'state',
        'table': 'TaxLotState',
        'displayName': 'State (Tax Lot)',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'postal_code',
        'table': 'PropertyState',
        'displayName': 'Postal Code (Property)',
        'type': 'numberStr',
        'duplicateNameInOtherTable': True
    }, {
        'name': 'postal_code',
        'table': 'TaxLotState',
        'displayName': 'Postal Code (Tax Lot)',
        'type': 'number',
        'duplicateNameInOtherTable': True
    }, {
        # INCOMPLETE, FIELD DOESN'T EXIST
        'name': 'primary_tax_lot_id',
        'table': None,
        'displayName': 'Primary Tax Lot ID',
        'type': 'number',
    }, {
        # FIELD DOESN'T EXIST
        'name': 'calculated_taxlot_ids',
        'table': None,
        'displayName': 'Associated TaxLot IDs',
        'type': 'numberStr',
    }, {
        # INCOMPLETE, FIELD DOESN'T EXIST
        'name': 'associated_building_tax_lot_id',
        'table': None,
        'displayName': 'Associated Building Tax Lot ID',
        'type': 'numberStr',
    }, {
        # INCOMPLETE, FIELD DOESN'T EXIST
        'name': 'associated_tax_lot_ids',
        'table': None,
        'displayName': 'Associated TaxLot IDs',
        'type': 'number',
    }, {
        # This field should never be mapped to!
        'name': 'lot_number',
        'table': 'PropertyState',
        'displayName': 'Associated Tax Lot ID',
        'type': 'numberStr',
    }, {
        'name': 'primary',
        'table': 'TaxLotState',
        'displayName': 'Primary/Secondary',
    }, {
        'name': 'property_name',
        'table': 'PropertyState',
        'displayName': 'Property Name',
    }, {
        'name': 'campus',
        'table': 'PropertyState',
        'displayName': 'Campus',
        'type': 'boolean',
    }, {
        'name': 'gross_floor_area',
        'table': 'PropertyState',
        'displayName': 'Gross Floor Area',
        'type': 'number',
    }, {
        'name': 'use_description',
        'table': 'PropertyState',
        'displayName': 'Use Description',
    }, {
        'name': 'energy_score',
        'table': 'PropertyState',
        'displayName': 'ENERGY STAR Score',
        'type': 'number',
    }, {
        'name': 'site_eui',
        'table': 'PropertyState',
        'displayName': 'Site EUI',
        'type': 'number',
    }, {
        'name': 'property_notes',
        'table': 'PropertyState',
        'displayName': 'Property Notes',
    }, {
        'name': 'property_type',
        'table': 'PropertyState',
        'displayName': 'Property Type',
    }, {
        'name': 'year_ending',
        'table': 'PropertyState',
        'displayName': 'Year Ending',
    }, {
        'name': 'owner',
        'table': 'PropertyState',
        'displayName': 'Owner',
    }, {
        'name': 'owner_email',
        'table': 'PropertyState',
        'displayName': 'Owner Email',
    }, {
        'name': 'owner_telephone',
        'table': 'PropertyState',
        'displayName': 'Owner Telephone',
    }, {
        'name': 'building_count',
        'table': 'PropertyState',
        'displayName': 'Building Count',
        'type': 'number',
    }, {
        'name': 'year_built',
        'table': 'PropertyState',
        'displayName': 'Year Built',
        'type': 'number',
    }, {
        'name': 'recent_sale_date',
        'table': 'PropertyState',
        'displayName': 'Recent Sale Date',
        'type': 'date',
        'cellFilter': 'date:\'MM-dd-yyyy\'',
    }, {
        'name': 'conditioned_floor_area',
        'table': 'PropertyState',
        'displayName': 'Conditioned Floor Area',
        'type': 'number',
    }, {
        'name': 'occupied_floor_area',
        'table': 'PropertyState',
        'displayName': 'Occupied Floor Area',
        'type': 'number',
    }, {
        'name': 'owner_address',
        'table': 'PropertyState',
        'displayName': 'Owner Address',
        'type': 'numberStr',
    }, {
        'name': 'owner_city_state',
        'table': 'PropertyState',
        'displayName': 'Owner City/State',
    }, {
        'name': 'owner_postal_code',
        'table': 'PropertyState',
        'displayName': 'Owner Postal Code',
        'type': 'number',
    }, {
        'name': 'home_energy_score_id',
        'table': 'PropertyState',
        'displayName': 'Home Energy Score ID',
        'type': 'numberStr',
    }, {
        'name': 'generation_date',
        'table': 'PropertyState',
        'displayName': 'PM Generation Date',
        'type': 'date',
        'cellFilter': 'date:\'MM-dd-yyyy\'',
    }, {
        'name': 'release_date',
        'table': 'PropertyState',
        'displayName': 'PM Release Date',
        'type': 'date',
        'cellFilter': 'date:\'MM-dd-yyyy\'',
    }, {
        'name': 'source_eui_weather_normalized',
        'table': 'PropertyState',
        'displayName': 'Source EUI Weather Normalized',
        'type': 'number',
    }, {
        'name': 'site_eui_weather_normalized',
        'table': 'PropertyState',
        'displayName': 'Site EUI Weather Normalized',
        'type': 'number',
    }, {
        'name': 'source_eui',
        'table': 'PropertyState',
        'displayName': 'Source EUI',
        'type': 'number',
    }, {
        'name': 'energy_alerts',
        'table': 'PropertyState',
        'displayName': 'Energy Alerts',
    }, {
        'name': 'space_alerts',
        'table': 'PropertyState',
        'displayName': 'Space Alerts',
    }, {
        'name': 'building_certification',
        'table': 'PropertyState',
        'displayName': 'Building Certification',
    }, {
        'name': 'number_properties',
        'table': 'TaxLotState',
        'displayName': 'Number Properties',
        'type': 'number',
    }, {
        'name': 'block_number',
        'table': 'TaxLotState',
        'displayName': 'Block Number',
        'type': 'number',
    }, {
        'name': 'district',
        'table': 'TaxLotState',
        'displayName': 'District',
    }
]
