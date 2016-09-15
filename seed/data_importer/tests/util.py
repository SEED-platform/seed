# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
PROPERTIES_MAPPING = [
    {
        "from_field": u'jurisdiction_tax_lot_id',
        "to_table_name": u'TaxLotState',
        "to_field": u'jurisdiction_tax_lot_id',
    }, {
        "from_field": u'jurisdiction_property_id',
        "to_table_name": u'PropertyState',
        "to_field": u'jurisdiction_property_id',
    }, {
        "from_field": u'pm_property_id',
        "to_table_name": u'PropertyState',
        "to_field": u'pm_property_id',
    }, {
        "from_field": u'pm_parent_property_id',
        "to_table_name": u'PropertyState',
        "to_field": u'pm_parent_property_id'
    }, {
        "from_field": u'address_line_1',
        "to_table_name": u'PropertyState',
        "to_field": u'address_line_1'
    }, {
        "from_field": u'city',
        "to_table_name": u'PropertyState',
        "to_field": u'city'
    }, {
        "from_field": u'property_name',
        "to_table_name": u'PropertyState',
        "to_field": u'property_name'
    }, {
        "from_field": u'property_notes',
        "to_table_name": u'PropertyState',
        "to_field": u'property_notes'
    }, {
        "from_field": u'use_description',
        "to_table_name": u'PropertyState',
        "to_field": u'use_description'
    }, {
        "from_field": u'gross_floor_area',
        "to_table_name": u'PropertyState',
        "to_field": u'gross_floor_area'
    }, {
        "from_field": u'owner',
        "to_table_name": u'PropertyState',
        "to_field": u'owner'
    }, {
        "from_field": u'owner_email',
        "to_table_name": u'PropertyState',
        "to_field": u'owner_email'
    }, {
        "from_field": u'owner_telephone',
        "to_table_name": u'PropertyState',
        "to_field": u'owner_telephone'
    }, {
        "from_field": u'site_eui',
        "to_table_name": u'PropertyState',
        "to_field": u'site_eui'
    }, {
        "from_field": u'energy_score',
        "to_table_name": u'PropertyState',
        "to_field": u'energy_score'
    }, {
        "from_field": u'year_ending',
        "to_table_name": u'PropertyState',
        "to_field": u'year_ending'
    }
]

FAKE_EXTRA_DATA = {
    u'City': u'EnergyTown',
    u'ENERGY STAR Score': u'',
    u'State/Province': u'Illinois',
    u'Site EUI (kBtu/ft2)': u'',
    u'Year Ending': u'',
    u'Weather Normalized Source EUI (kBtu/ft2)': u'',
    u'Parking - Gross Floor Area (ft2)': u'',
    u'Address 1': u'000015581 SW Sycamore Court',
    u'Property Id': u'101125',
    u'Address 2': u'Not Available',
    u'Source EUI (kBtu/ft2)': u'',
    u'Release Date': u'',
    u'National Median Source EUI (kBtu/ft2)': u'',
    u'Weather Normalized Site EUI (kBtu/ft2)': u'',
    u'National Median Site EUI (kBtu/ft2)': u'',
    u'Year Built': u'',
    u'Postal Code': u'10108-9812',
    u'Organization': u'Occidental Management',
    u'Property Name': u'Not Available',
    u'Property Floor Area (Buildings and Parking) (ft2)': u'',
    u'Total GHG Emissions (MtCO2e)': u'',
    u'Generation Date': u'',
}

FAKE_ROW = {
    u'Name': u'The Whitehouse',
    u'Address Line 1': u'1600 Pennsylvania Ave.',
    u'Year Built': u'1803',
    u'Double Tester': 'Just a note from bob'
}

FAKE_MAPPINGS = {
    'full': [
        {
            'property_name': u'Name',
            'address_line_1': u'Address Line 1',
            'year_built': u'Year Built'
        },
        {
            "from_field": u'Year Built',
            "to_table_name": u'PropertyState',
            "to_field": u'year_built',
        },
        {
            "from_field": u'Address Line 1',
            "to_table_name": u'PropertyState',
            "to_field": u'address_line_1',
        }
    ],
    'short': {
        'property_name': u'Name',
        'address_line_1': u'Address Line 1',
        'year_built': u'Year Built'
    },
}
