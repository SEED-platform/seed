# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from __future__ import absolute_import

import logging

from buildingsync_asset_extractor.processor import BSyncProcessor as BAE

from seed.building_sync.building_sync import BuildingSync
from seed.building_sync.mappings import (
    BASE_MAPPING_V2,
    merge_mappings,
    xpath_to_column_map
)

_log = logging.getLogger(__name__)


def build_column_mapping(base_mapping=None, custom_mapping=None):
    if base_mapping is None:
        base_mapping = BuildingSync.VERSION_MAPPINGS_DICT[BuildingSync.BUILDINGSYNC_V2_0]
    merged_map = merge_mappings(base_mapping, custom_mapping)
    column_mapping = xpath_to_column_map(merged_map)
    return {
        xpath: ('PropertyState', db_column, 100)
        for xpath, db_column in column_mapping.items()
    }


def get_valid_units():
    # taken from mapping partial (./static/seed/partials/mapping.html)
    valid_units = [
        # area units
        "ft**2",
        "m**2",
        # eui_units
        "kBtu/ft**2/year",
        "kWh/m**2/year",
        "GJ/m**2/year",
        "MJ/m**2/year",
        "kBtu/m**2/year"
    ]
    return valid_units


def get_bae_mappings():
    """ returns the default BAE assets ready for import"""
    results = []

    # nothing should have units since they are stored in a separate dedicated field
    # export_units field indicates fields that have a separate units field.
    # units field name is the same with " Units" appended.

    bsync_assets = BAE.get_default_asset_defs()
    for item in bsync_assets:

        if item['type'] == 'sqft':
            # these types need 2 different entries: 1 for "primary" and 1 for "secondary"
            for i in ['Primary', 'Secondary']:
                results.append(make_bae_hash(i + ' ' + item['export_name']))
                if 'export_units' in item and item['export_units'] is True:
                    # also export units field
                    results.append(make_bae_hash(i + ' ' + item['export_name'] + " Units"))

        else:
            results.append(make_bae_hash(item['export_name']))
            if 'export_units' in item and item['export_units'] is True:
                results.append(make_bae_hash(item['export_name'] + " Units"))

    return results


def make_bae_hash(name):
    return {'from_field': name,
            'from_field_value': 'text',  # hard code this for now
            'from_units': None,
            'to_field': name,
            'to_table_name': 'PropertyState'}


def default_buildingsync_profile_mappings():
    """Returns the default ColumnMappingProfile mappings for BuildingSync
    :return: list
    """
    valid_units = get_valid_units()

    mapping = BASE_MAPPING_V2.copy()
    base_path = mapping['property']['xpath'].rstrip('/')
    result = []
    for col_name, col_info in mapping['property']['properties'].items():
        from_units = col_info.get('units')
        if from_units not in valid_units:
            from_units = None

        sub_path = col_info['xpath'].replace('./', '')
        absolute_xpath = f'{base_path}/{sub_path}'
        result.append({
            'from_field': absolute_xpath,
            'from_field_value': col_info['value'],
            'from_units': from_units,
            'to_field': col_name,
            'to_table_name': 'PropertyState'
        })

    # also grab BAE mappings
    bae_results = get_bae_mappings()
    result.extend(bae_results)

    return result
