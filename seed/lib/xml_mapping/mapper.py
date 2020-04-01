# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import
import logging

from seed.building_sync.mappings import merge_mappings, xpath_to_column_map

_log = logging.getLogger(__name__)


def build_column_mapping(base_mapping, custom_mapping=None):
    merged_map = merge_mappings(base_mapping, custom_mapping)
    column_mapping = xpath_to_column_map(merged_map)
    return {
        xpath: ('PropertyState', db_column, 100)
        for xpath, db_column in column_mapping.items()
    }
