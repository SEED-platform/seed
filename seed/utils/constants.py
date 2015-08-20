EXCLUDE_FIELDS = [
    'best_guess_canonical_building',
    'best_guess_confidence',
    'canonical_building',
    'canonical_for_ds',
    'children',
    'confidence',
    'created',
    'extra_data',
    'id',
    'import_file',
    'last_modified_by',
    'match_type',
    'modified',
    'parents',
    'pk',
    'seed_org',
    'source_type',
    'super_organization',
    'duplicate',
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
    }
]

ASSESSOR_FIELDS_BY_COLUMN = {field['sort_column']: field
                             for field in ASSESSOR_FIELDS}
