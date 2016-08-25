# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Nicholas Long <nicholas.long@nrel.gov>
"""
import logging

from seed.models import PropertyState, TaxLotState
from seed.utils import constants

_log = logging.getLogger(__name__)


class MappingData(object):
    """
    New format for managing looking up mapping data. This includes a more
    comprehensive set of data fields with type and schema information

    Makes a dictionary of the column names and their respective types.

    .. todo:

        Build this dictionary from BEDES fields (the null organization columns,
        and all of the column mappings that this organization has previously
        saved.

    """

    def __init__(self, exclude_fields=None):
        if not exclude_fields:
            exclude_fields = constants.EXCLUDE_FIELDS

        # So bedes compliant fields are defined in the database? That is strange
        self.data = []

        for f in PropertyState._meta.fields:
            # _source have been removed from new data model
            if f.name not in exclude_fields:  # and '_source' not in f.name:
                self.data.append(
                    {
                        'table': 'PropertyState',
                        'name': f.name,
                        'type': f.get_internal_type() if f.get_internal_type else 'string',
                        'js_type': self.normalize_mappable_type(
                            f.get_internal_type()),
                        'schema': 'BEDES',
                        'extra_data': False,
                    }
                )

        for f in TaxLotState._meta.fields:
            # _source have been removed from new data model
            if f.name not in exclude_fields:  # and '_source' not in f.name:
                self.data.append(
                    {
                        'table': 'TaxLotState',
                        'name': f.name,
                        'type': f.get_internal_type() if f.get_internal_type else 'string',
                        'js_type': self.normalize_mappable_type(
                            f.get_internal_type()),
                        'schema': 'BEDES',
                        'extra_data': False,
                    }
                )

        self.sort_data()

    def normalize_mappable_type(self, in_str):
        """
        Normalize the data types for when we communicate the fields in
        JavaScript.

        Args:
            in_str: string to normalize

        Returns: normalized string with JavaScript data types

        """

        return in_str.lower().replace('field', ''). \
            replace('integer', 'float'). \
            replace('time', ''). \
            replace('text', ''). \
            replace('char', '')

    def add_extra_data(self, columns):
        """
        Add in the unit types from a columns queryset

        Args:
            columns: list of columns from the Column table

        Returns: None

        """
        for c in columns:
            unit = c.unit.get_unit_type_display().lower() if c.unit else 'string'
            self.data.append(
                {
                    'name': c.column_name,
                    'type': unit,
                    'js_type': self.normalize_mappable_type(unit),
                    'schema': 'BEDES',
                    'table': 'PropertyState',
                    'extra_data': True,
                }
            )

        self.sort_data()

    def keys(self):
        """
        Flatten the data set to a list of unique names independent of the
        table.

        Returns: List of keys
        """

        result = set()
        for d in self.data:
            result.add(d['name'])

        return list(sorted(result))


    def building_columns(self):
        """
        Return a set of the sorted keys which are the possible columns

        Returns: set of keys

        """

        return list(set(sorted(self.keys())))

    def extra_data(self):
        """
        List only the extra_data columns, that is the columns that are not
        database fields.

        Returns: set of keys of the extra_data columns

        """

        f = None
        try:
            f = [item for item in self.data if item['extra_data']]
        except StopIteration:
            pass

        return f

    def sort_data(self):
        """
        sort the objects by table . name

        Returns: None, updates member variable

        """
        self.data = sorted(self.data,
                           key=lambda k: (k['table'].lower(), k['name']))

    def find_column(self, table_name, column_name):
        """

        Args:
            table_name: name of the table to find
            column_name: name of the column to find with the correct table

        Returns: None or Dict of found column

        """

        table_name = table_name.lower()
        column_name = column_name.lower()

        f = None
        try:
            f = (item for item in self.data if
                 item['name'].lower() == column_name and
                 item['table'].lower() == table_name).next()
        except StopIteration:
            pass

        return f
