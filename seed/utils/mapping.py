# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from seed.models import BuildingSnapshot
from seed.utils import constants


def get_mappable_columns(exclude_fields=None):
    """Get a list of all the columns we're able to map to."""
    return get_mappable_types(exclude_fields).keys()


def get_mappable_types(exclude_fields=None):
    """Like get_mappable_columns, but with type information."""
    if not exclude_fields:
        exclude_fields = constants.EXCLUDE_FIELDS

    results = {}
    for f in BuildingSnapshot._meta.fields:
        if f.name not in exclude_fields and '_source' not in f.name:
            results[f.name] = f.get_internal_type()

    # Normalize the types for when we communicate with JS.
    for field in results:
        results[field] = results[field].lower().replace(
            'field', ''
        ).replace(
            'integer', 'float'
        ).replace(
            'time', ''
        ).replace(
            'text', ''
        ).replace(
            'char', ''
        )

    return results


def _get_column_names(column_mapping, attr_name='column_raw'):
    """Turns the Column.column_names into a serializable list of str."""
    attr = getattr(column_mapping, attr_name, None)
    if not attr:
        return attr
    return [
        t for t in attr.all().values_list('column_name', flat=True)
    ]
