# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging


logger = logging.getLogger(__name__)

TAXLOT_MAPPING = [
    {
        "from_field": 'jurisdiction_tax_lot_id',
        "to_table_name": 'TaxLotState',
        "to_field": 'jurisdiction_tax_lot_id',
    },
    {
        "from_field": 'address',
        "to_table_name": 'TaxLotState',
        "to_field": 'address_line_1'
    },
    {
        "from_field": 'city',
        "to_table_name": 'TaxLotState',
        "to_field": 'city'
    },
    {
        "from_field": 'number_buildings',
        "to_table_name": 'TaxLotState',
        "to_field": 'number_properties'
    },
    {
        "from_field": 'block_number',
        "to_table_name": 'TaxLotState',
        "to_field": 'block_number'
    },
    {
        'from_field': 'postal code',
        'to_table_name': 'TaxLotState',
        'to_field': 'postal_code',
    }
]

PROPERTIES_MAPPING = [
    {
        "from_field": 'jurisdiction tax lot id',
        "to_table_name": 'TaxLotState',
        "to_field": 'jurisdiction_tax_lot_id',
    }, {
        "from_field": 'jurisdiction property id',
        "to_table_name": 'PropertyState',
        "to_field": 'jurisdiction_property_id',
    }, {
        "from_field": 'pm property id',
        "to_table_name": 'PropertyState',
        "to_field": 'pm_property_id',
    }, {
        "from_field": 'UBID',
        "to_table_name": 'PropertyState',
        "to_field": 'ubid',
    }, {
        "from_field": 'custom id 1',
        "to_table_name": 'PropertyState',
        "to_field": 'custom_id_1',
    }, {
        "from_field": 'pm parent property id',
        "to_table_name": 'PropertyState',
        "to_field": 'pm_parent_property_id'
    }, {
        "from_field": 'address line 1',
        "to_table_name": 'PropertyState',
        "to_field": 'address_line_1'
    }, {
        "from_field": 'city',
        "to_table_name": 'PropertyState',
        "to_field": 'city'
    }, {
        "from_field": 'property name',
        "to_table_name": 'PropertyState',
        "to_field": 'property_name'
    }, {
        "from_field": 'property notes',
        "to_table_name": 'PropertyState',
        "to_field": 'property_notes'
    }, {
        "from_field": 'use description',
        "to_table_name": 'PropertyState',
        "to_field": 'use_description'
    }, {
        "from_field": 'gross floor area',
        "to_table_name": 'PropertyState',
        "to_field": 'gross_floor_area'
    }, {
        "from_field": 'owner',
        "to_table_name": 'PropertyState',
        "to_field": 'owner'
    }, {
        "from_field": 'owner email',
        "to_table_name": 'PropertyState',
        "to_field": 'owner_email'
    }, {
        "from_field": 'owner telephone',
        "to_table_name": 'PropertyState',
        "to_field": 'owner_telephone'
    }, {
        "from_field": 'site eui',
        "to_table_name": 'PropertyState',
        "to_field": 'site_eui'
    }, {
        "from_field": 'energy score',
        "to_table_name": 'PropertyState',
        "to_field": 'energy_score'
    }, {
        "from_field": 'year ending',
        "to_table_name": 'PropertyState',
        "to_field": 'year_ending'
    }, {
        "from_field": 'extra data 1',
        "to_table_name": 'PropertyState',
        "to_field": 'data_007'
    }, {
        "from_field": 'extra data 2',
        "to_table_name": 'TaxLotState',
        "to_field": 'data_008'
    }, {
        "from_field": 'recent sale date',
        "to_table_name": 'PropertyState',
        "to_field": 'recent_sale_date'
    }, {
        'from_field': 'postal code',
        'to_table_name': 'PropertyState',
        'to_field': 'postal_code',
    }
]

FAKE_EXTRA_DATA = {
    'City': 'EnergyTown',
    'ENERGY STAR Score': '',
    'State/Province': 'Illinois',
    'Site EUI (kBtu/ft2)': '',
    'Year Ending': '',
    'Weather Normalized Source EUI (kBtu/ft2)': '',
    'Parking - Gross Floor Area (ft2)': '',
    'Address 1': '000015581 SW Sycamore Court',
    'Property Id': '101125',
    'Address 2': 'Not Available',
    'Source EUI (kBtu/ft2)': '',
    'Release Date': '',
    'National Median Source EUI (kBtu/ft2)': '',
    'Weather Normalized Site EUI (kBtu/ft2)': '',
    'National Median Site EUI (kBtu/ft2)': '',
    'Year Built': '',
    'Postal Code': '10108-9812',
    'Organization': 'Occidental Management',
    'Property Name': 'Not Available',
    'Property Floor Area (Buildings and Parking) (ft2)': '',
    'Total GHG Emissions (MtCO2e)': '',
    'Generation Date': '',
}

FAKE_ROW = {
    'Name': 'The Whitehouse',
    'Address Line 1': '1600 Pennsylvania Ave.',
    'Year Built': '1803',
    'Double Tester': 'Just a note from bob'
}

FAKE_MAPPINGS = {
    'portfolio': PROPERTIES_MAPPING,
    'taxlot': TAXLOT_MAPPING,
    'covered_building': [
        {
            'from_field': 'City',  # raw field in import file
            'to_field': 'city',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'GBA',  # raw field in import file
            'to_field': 'gross_floor_area',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'BLDGS',  # raw field in import file
            'to_field': 'building_count',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'UBI',  # raw field in import file
            'to_field': 'jurisdiction_tax_lot_id',
            'to_table_name': 'TaxLotState',
        }, {
            'from_field': 'UBID',  # raw field in import file
            'to_field': 'ubid',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'State',  # raw field in import file
            'to_field': 'state_province',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'Address',  # raw field in import file
            'to_field': 'address_line_1',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'Owner',  # raw field in import file
            'to_field': 'owner',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'Property Type',  # raw field in import file
            'to_field': 'use_description',
            'to_table_name': 'PropertyState',
        }, {
            'from_field': 'AYB_YearBuilt',  # raw field in import file
            'to_field': 'year_built',
            'to_table_name': 'PropertyState',
        }],
    'full': [
        {
            "from_field": 'Name',
            "to_table_name": 'PropertyState',
            "to_field": 'property_name',
        }, {
            "from_field": 'Address Line 1',
            "to_table_name": 'PropertyState',
            "to_field": 'address_line_1',
        }, {
            "from_field": 'Year Built',
            "to_table_name": 'PropertyState',
            "to_field": 'year_built',
        }, {
            "from_field": 'Double Tester',
            "to_table_name": 'PropertyState',
            "to_field": 'Double Tester',
        }

    ],
    'fake_row': [
        {
            "from_field": 'Name',
            "to_table_name": 'PropertyState',
            "to_field": 'property_name',
        }, {
            "from_field": 'Address Line 1',
            "to_table_name": 'PropertyState',
            "to_field": 'address_line_1',
        }, {
            "from_field": 'Year Built',
            "to_table_name": 'PropertyState',
            "to_field": 'year_built',
        }, {
            "from_field": 'Double Tester',
            "to_table_name": 'PropertyState',
            "to_field": 'Double Tester',
        }
    ],
    'short': {  # Short should no longer be used and probably does not work anymore.
        'property_name': 'Name',
        'address_line_1': 'Address Line 1',
        'year_built': 'Year Built'
    },
}

TAXLOT_FOOTPRINT_MAPPING = {
    "from_field": 'Tax Lot Coordinates',
    "to_table_name": 'TaxLotState',
    "to_field": 'taxlot_footprint',
}
PROPERTY_FOOTPRINT_MAPPING = {
    "from_field": 'Property Coordinates',
    "to_table_name": 'PropertyState',
    "to_field": 'property_footprint',
}
