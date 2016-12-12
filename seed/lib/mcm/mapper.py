# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import logging
import re

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


def apply_column_value(raw_field, value, model, mapping, is_extra_data, cleaner):
    """Set the column value as the target attr on our model.

    :param raw_field: str, the raw imported column name as the mapping understands it.
    :param value: dict, the value of that column for a given row.
    :param model: inst, the object we're mapping data to.
    :param mapping: dict, the mapping of row data to attribute data.
    :param is_extra_data: bool, is the column supposed to be extra_data
    :param cleaner: runnable, something to clean data values.

    :rtype: model inst
    """
    cleaned_value = None
    tmp_field = raw_field

    if cleaner:
        if tmp_field not in (cleaner.float_columns or cleaner.date_columns):
            # Try using a reverse mapping for dynamic maps;
            # default to row name if it's not mapped
            tmp_field = mapping.get(raw_field)
            if tmp_field:
                tmp_field = tmp_field[1]

                # TODO: there are a lot of warnings right now because we iterate over the header
                # of the file instead of iterating over the fields that we want to map.

                # else:
                # _log.warn("Could not find the field to clean: %s" % raw_field)

        cleaned_value = cleaner.clean_value(value, tmp_field)
    else:
        cleaned_value = default_cleaner(value)

    # If the item is the extra_data column, then make sure to save it to the
    # extra_data field of the database
    if raw_field in mapping:
        table_name, field_name = mapping.get(raw_field)
        # _log.debug("item is in the mapping: %s -- %s" % (table_name, field_name))

        # NL: 9/29/16 turn off all the debug logging because it was too verbose.
        if is_extra_data:
            if hasattr(model, 'extra_data'):
                # only save it if the model and the mapping are the same
                if model.__class__.__name__ == table_name:
                    model.extra_data[raw_field] = cleaned_value
                    # else:
                    #     _log.debug(
                    #         "model name '%s' is not the same as the mapped table name '%s' -- skipping field '%s'" % (
                    #         model.__class__.__name__, table_name, field_name))  # noqa
                    # else:
                    #     _log.debug(
                    #         "model object does not have extra_data field, skipping mapping for %s" % raw_field)  # noqa
        else:
            # Simply set the field to the cleaned value if it is the correct model
            if model.__class__.__name__ == table_name:
                setattr(model, field_name, cleaned_value)
                # else:
                #     _log.debug(
                #         "model name '%s' is not the same as the mapped table name '%s' -- skipping field '%s'" % (
                #             model.__class__.__name__, table_name, field_name))  # noqa

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
    return value.strip().upper().replace(
        '-', ''
    ).replace(
        ' ', ''
    ).replace(
        '/', ''
    ).replace(
        '\\', ''
    )


def expand_field(field):
    """
    take a field from the csv and expand/split on a delimiter and return a list of individual values

    :param field: str, value to parse

    :return: list of individual values after after delimiting
    """

    if isinstance(field, str) or isinstance(field, unicode):
        return [_normalize_expanded_field(r) for r in re.split(",|;|:", field)]
    else:
        return [field]


def expand_rows(row, delimited_field):
    """
    Take a row and a field which may have delimited values and convert into a list of new rows
    with the same data expect for the replaced delimited value.

    :param row: dict, original row to split out
    :param delimited_field: string - column to try and split

    :return: list
    """

    # does the chosen delimited field even exist in the row dict?
    if delimited_field not in row:
        return [row]
    else:
        new_values = expand_field(row[delimited_field])
        new_rows = []
        for v in new_values:
            new_row = copy.deepcopy(row)
            new_row[delimited_field] = v
            new_rows.append(new_row)

        return new_rows


def map_row(row, mapping, model_class, extra_data_fields=[], cleaner=None, concat=None, **kwargs):
    """Apply mapping of row data to model.

    :param original_row: dict, parsed row data from csv.
    :param mapping: dict, keys map row columns to model_class attrs.
    :param model_class: class, reference to model class we map against.
    :param extra_data_fields: list, list of raw columns that are considered extra data (per mapping)
    :param cleaner: (optional) inst, cleaner instance for row values.
    :param concat: (optional) list of dict, config for concatenating rows into an attr.

    :rtype: list of model instances that were created

    """
    initial_data = kwargs.get('initial_data', None)
    model = model_class()

    # If there are any initial states we need to set prior to mapping.
    if initial_data:
        model = apply_initial_data(model, initial_data)

    # concat is not used as of 2016-09-14
    # concat = _set_default_concat_config(concat)

    # In case we need to look up cleaner by dynamic field mapping.
    # TODO: we should flip this around and iterate over the mappings because there is a lot
    # of extra work being done (sometimes) when the columns are being split across two
    # different data base objects (i.e. taxlotstate and propertystate)
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
