# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
# TODO: Merge this file with other schema
# https://github.com/SEED-platform/seed/blob/41c104cd105161c949e9cb379aac946ea9202c74/seed/lib/mappings/mapping_data.py  # noqa

# These are fields that are ignored when using methods that automatically determine names and
# cloning records
EXCLUDE_FIELDS = [
    'best_guess_canonical_building',
    'best_guess_confidence',
    'canonical_building',
    'canonical_for_ds',
    'children',
    'confidence',
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
    # Do not map to the original fields that are no longer quantities
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
