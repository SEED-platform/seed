# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import itertools
import logging
import re
from datetime import datetime, date

from cleaners import default_cleaner
from seed.lib.mappings.mapping_columns import MappingColumns

_log = logging.getLogger(__name__)


def build_pm_mapping():
    """
    Build the Portfolio Manager mappings.

    :return:
    """

    return True


def build_column_mapping(raw_columns, dest_columns, previous_mapping=None, map_args=None, thresh=0):
    """
    Wrapper around the MappingColumns class to create the list of suggested mappings

    Args:
        raw_columns: list of str. The column names we're trying to map.
        dest_columns: list of str. The columns we're mapping to.
        previous_mapping:  callable. Used to return the previous mapping
            for a given field.

            .. code:

                The expectation is that our callable always gets passed a raw key. If
                it finds a match, it returns the raw_column and score.
                previous_mapping('example field', *map_args) ->
                    ('field_1', 0.93)

        map_args: .. todo: document
        thresh: .. todo: document

    Returns:
        dict: {'raw_column': ('dest_column', score)

    """

    return MappingColumns(raw_columns, dest_columns, previous_mapping, map_args,
                          thresh).final_mappings


def apply_initial_data(model, initial_data):
    """Set any attributes that are passed in as initial data.

    :param model: instance of your state tracking object.
    :param initial_data: dict, keys should line up with attributes on model.
    :rtype: model instance, modified.

    """
    for item in initial_data:
        value = initial_data[item]
        if hasattr(model, item):
            setattr(model, item, value)
        elif hasattr(model, 'extra_data') and isinstance(model.extra_data, dict):
            model.extra_data[item] = value

    return model


def _concat_values(concat_columns, column_values, delimiter):
    """Concatenate the values into one string to set for target."""
    # Use the order of values that we got from concat_columns def.
    values = [
        column_values[item] for item in concat_columns if item in column_values
    ]
    return delimiter.join(values) or None


def apply_column_value(raw_column_name, column_value, model, mapping, is_extra_data, cleaner):
    """Set the column value as the target attr on our model.

    :param raw_column_name: str, the raw imported column name as the mapping understands it.
    :param column_value: dict, the value of that column for a given row.
    :param model: inst, the object we're mapping data to.
    :param mapping: dict, the mapping of row data to attribute data.
    :param is_extra_data: bool, is the column supposed to be extra_data
    :param cleaner: runnable, something to clean data values.

    :rtype: model inst
    """

    # If the item is the extra_data column, then make sure to save it to the
    # extra_data field of the database
    if raw_column_name in mapping:
        table_name, mapped_column_name = mapping.get(raw_column_name)
        # NL: 9/29/16 turn off all the debug logging because it was too verbose.
        # _log.debug("item is in the mapping: %s -- %s" % (table_name, field_name))

        cleaned_value = None
        if cleaner:
            cleaned_value = cleaner.clean_value(column_value, mapped_column_name)
        else:
            cleaned_value = default_cleaner(column_value)

        if is_extra_data:
            if hasattr(model, 'extra_data'):
                # only save it if the model and the mapping are the same
                if model.__class__.__name__ == table_name:
                    if isinstance(cleaned_value, (datetime, date)):
                        # TODO: create an encoder for datetime once we are in Django 1.11
                        model.extra_data[mapped_column_name] = cleaned_value.isoformat()
                    else:
                        model.extra_data[mapped_column_name] = cleaned_value
        else:
            # Simply set the field to the cleaned value if it is the correct model
            if model.__class__.__name__ == table_name:
                setattr(model, mapped_column_name, cleaned_value)

    return model


def _set_default_concat_config(concat):
    """Go through the list of dictionaries and setup their keys."""
    concat = concat or []
    if not isinstance(concat, list):
        concat = [concat]
    for c in concat:
        c['target'] = c.get('target', '__broken_target__')
        c['concat_columns'] = c.get('concat_columns', [])
        c['delimiter'] = c.get('delimiter', ' ')
        c['concat_values'] = {}

    return concat


def _normalize_expanded_field(value):
    """
    Fields that are expanded (typically tax lot id) are also in need of normalization to remove
    characters that prevent easy matching.

    This method will remove unwanted characters from the jurisdiction tax lot id.

    :param value: string
    :return: string
    """
    return re.sub(r'[-\s/\\]', '', value).upper()


def expand_and_normalize_field(field, return_list=False):
    """
    take a field from the csv and expand/split on a delimiter and return a list of individual
    values. If the return_list flag is set to true, then this method will return the data back
    as a list of new fields instead of a cleaned up string and normalized with semicolon delimiter

    :param field: str, value to parse

    :return: list of individual values after after delimiting
    """

    if isinstance(field, str) or isinstance(field, unicode):
        field = field.rstrip(';:,')
        data = [_normalize_expanded_field(r) for r in re.split(",|;|:", field)]
        if return_list:
            return data
        else:
            return ";".join(data)
    else:
        if return_list:
            return [field]
        else:
            return field


def expand_rows(row, delimited_fields, expand_row):
    """
    Take a row and a field which may have delimited values and convert into a list of new rows
    with the same data expect for the replaced delimited value.

    :param row: dict, original row to split out
    :param delimited_fields: list of dicts, columns to clean/expand/split
    :param expand_row: boolean, expand the row on delimited fields or not.

    :return: list
    """

    # _log.debug('expand_row is {}'.format(expand_row))
    # go through the delimited fields and clean up the rows
    copy_row = copy.deepcopy(row)
    for d in delimited_fields:
        if d in copy_row:
            copy_row[d] = expand_and_normalize_field(copy_row[d], False)

    if expand_row:
        new_values = []
        for d in delimited_fields:
            fields = []
            if d in copy_row.keys():
                for value in expand_and_normalize_field(copy_row[d], True):
                    fields.append({d: value})
                new_values.append(fields)

        # return all combinations of the lists
        combinations = list(itertools.product(*new_values))

        new_rows = []
        for c in combinations:
            new_row = copy.deepcopy(copy_row)
            # c is a tuple because of the .product command
            for item in c:
                for k, v in item.iteritems():
                    new_row[k] = v
            new_rows.append(new_row)

        return new_rows
    else:
        return [copy_row]


def map_row(row, mapping, model_class, extra_data_fields=[], cleaner=None, **kwargs):
    """Apply mapping of row data to model.

    :param row: dict, parsed row data from csv.
    :param mapping: dict, keys map row columns to model_class attrs.
    :param model_class: class, reference to model class we map against.
    :param extra_data_fields: list, list of raw columns that are considered extra data (per mapping)
    :param cleaner: (optional) inst, cleaner instance for row values.
    :param concat: (optional) list of dict, config for concatenating rows into an attr.

    :rtype: list of model instances that were created

    """
    initial_data = kwargs.get('initial_data', None)
    model = model_class()

    # _log.debug("map_row's mappings {}".format(mapping))

    # If there are any initial states we need to set prior to mapping.
    if initial_data:
        model = apply_initial_data(model, initial_data)

    # concat is not used as of 2016-09-14
    # concat = _set_default_concat_config(concat)

    for raw_field, value in row.items():
        # Look through any of our concatenation configs to see if this row
        # needs to be set aside for merging with others at the end of the map.
        #
        # concat is not used as of 2016-09-14
        # for concat_column in concat:
        #     if item in concat_column['concat_columns']:
        #         concat_column['concat_values'][item] = value
        #         continue

        # If our item is a column which requires that we apply the function
        # then, send_apply_func will reference this function and be sent
        # to the ``apply_column_value`` function.
        is_extra_data = True if raw_field in extra_data_fields else False

        # Save the value if is is not None, keep empty fields.
        if value is not None:
            model = apply_column_value(raw_field, value, model, mapping, is_extra_data, cleaner)

    # concat is not used as of 2016-09-14
    # if concat and [c['concat_values'] for c in concat]:
    #     # We've skipped mapping any columns which we're going to concat.
    #     # Now we concatenate them all and save to their designated target.
    #     for c in concat:
    #         mapping[c['target']] = c['target']
    #         concated_vals = _concat_values(
    #             c['concat_columns'],
    #             c['concat_values'],
    #             c['delimiter']
    #         )
    #         model = apply_column_value(c['target'], concated_vals, model, mapping, apply_columns,
    #                                    cleaner, apply_func=apply_func)

    return model
