# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Nicholas Long <nicholas.long@nrel.gov>
"""
import logging

from django.apps import apps

_log = logging.getLogger(__name__)


class MappingData(object):
    """
    New format for managing looking up mapping data. This includes a more
    comprehensive set of data fields with type and schema information

    Makes a dictionary of the column names and their respective types.

    MappingData data property contains the list of fields in the database with the table name.

    .. todo:

        Build this dictionary from BEDES fields (the null organization columns,
        and all of the column mappings that this organization has previously
        saved.

    """

    def __init__(self, organization_id):
        self.data = apps.get_model('seed', 'Column').retrieve_mapping_columns(organization_id)
        self.property_state_data = []
        self.tax_lot_state_data = []

        self.sort_data()

    def _normalize_mappable_type(self, in_str):
        """
        Normalize the data types for when we communicate the fields in JavaScript. ensures that the data
        types are consistent.

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
            _log.debug("Adding extra data column for table {} and column {}".format(c.column_name, c.table_name))
            self.data.append(
                {
                    'column_name': c.column_name,
                    'type': unit,
                    'table_name': c.table_name,
                    'is_extra_data': True,
                }
            )

        self.sort_data()

    @property
    def keys(self):
        """
        Flatten the data set to a list of unique names independent of the
        table.

        Returns: List of keys
        """

        result = set()
        for d in self.data:
            result.add(d['column_name'])

        return list(sorted(result))

    @property
    def keys_with_table_names(self):
        """
        Similar to keys, except it returns a list of tuples

        Returns: list of tuples

        .. code:
            [
              ('PropertyState', 'address_line_1'),
              ('PropertyState', 'address_line_2'),
              ('PropertyState', 'building_certification'),
              ('PropertyState', 'building_count'),
              ('TaxLotState', 'address_line_1'),
              ('TaxLotState', 'address_line_2'),
              ('TaxLotState', 'block_number'),
              ('TaxLotState', 'city'),
              ('TaxLotState', 'jurisdiction_tax_lot_id'),
            ]

        """
        result = set()
        for d in self.data:
            result.add((d['table_name'], d['column_name']))

        return list(sorted(result))

    @property
    def building_columns(self):
        """
        Return a set of the sorted keys which are the possible columns

        Returns: set of keys

        """

        return list(set(sorted(self.keys)))

    @property
    def extra_data(self):
        """
        List only the extra_data columns, that is the columns that are not
        database fields.

        Returns: set of keys of the extra_data columns

        """

        f = None
        try:
            f = [item for item in self.data if item['is_extra_data']]
        except StopIteration:
            pass

        return f

    def sort_data(self):
        """
        sort the objects by table . name

        Returns: None, updates member variable

        """
        self.data = sorted(self.data, key=lambda k: (k['table_name'].lower(), k['column_name']))

        # Only look at the property state and tax lot state. The fields that are on Property and Tax Lot just ignore
        # for now.
        self.property_state_data = sorted([x for x in self.data if x['table_name'] == 'PropertyState'],
                                          key=lambda k: (k['table_name'].lower(), k['column_name']))

        self.tax_lot_state_data = sorted([x for x in self.data if x['table_name'] == 'TaxLotState'],
                                         key=lambda k: (k['table_name'].lower(), k['column_name']))

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
            f = (
                item for item in self.data if
                item['table_name'].lower() == table_name and item['column_name'].lower() == column_name
            ).next()
        except StopIteration:
            pass

        return f
