# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import logging

import matchers
from cleaners import default_cleaner

_log = logging.getLogger(__name__)


def build_column_mapping(raw_columns, dest_columns, previous_mapping=None,
                         map_args=None, thresh=0):
    """
    Build a probabilistic mapping structure for mapping raw to dest.

    Args:
        raw_columns: list of str. The column names we're trying to map.
        dest_columns: list of str. The columns we're mapping to.
        previous_mapping:  callable. Used to return the previous mapping
            for a given field.

            .. code:

                # The expectation is that our callable always gets passed a
                # raw key. If it finds a match, it returns the raw_column and score.
                previous_mapping('example field', *map_args) ->
                    ('field_1', 0.93)

        map_args: .. todo: document
        thresh: .. todo: document

    Returns:
        dict: {'raw_column': [('dest_column', score)...],...}

    """

    probable_mapping = {}
    for raw in raw_columns:
        result = []
        result_table = None
        conf = 0
        # We want previous mappings to be at the top of the list.
        if previous_mapping and callable(previous_mapping):
            args = map_args or []
            mapping = previous_mapping(raw, *args)
            if mapping:
                result_table, result, conf = mapping

        # Only enter this flow if we haven't already selected a result. Ignore
        # blank columns with conf of 100 since a conf of 100 signifies the user
        # has saved that mapping.
        if not result and result is not None and conf != 100:
            table, best_match, conf = matchers.best_match(
                raw, dest_columns, top_n=1
            )[0]
            if conf > thresh:
                result = best_match
                result_table = table
            else:
                result = None
                conf = 0

        probable_mapping[raw] = [result_table, result, conf]

    return probable_mapping


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
    :param cleaner: runnable, something to clean data values.
    :param is_extra_data: bool, is the column supposed to be extra_data
    :param apply: (optional), function to apply value to our model.
    :rtype: model inst

    """
    # _log.debug("item is %s" % item)
    # _log.debug("value is %s" % value)
    # _log.debug("model is %s" % model)
    # _log.debug("mapping is %s" % mapping)
    # _log.debug("is_extra_data is %s" % is_extra_data)

    cleaned_value = None
    tmp_field = raw_field

    if cleaner:
        if tmp_field not in (cleaner.float_columns or cleaner.date_columns):
            # Try using a reverse mapping for dynamic maps;
            # default to row name if it's not mapped
            tmp_field = mapping.get(raw_field)
            if tmp_field:
                tmp_field = tmp_field[1]
            else:
                _log.warn("Could not find the field to clean: %s" % raw_field)

        cleaned_value = cleaner.clean_value(value, tmp_field)
    else:
        cleaned_value = default_cleaner(value)

    # If the item is the extra_data column, then make sure to save it to the
    # extra_data field of the database
    if raw_field in mapping:
        table_name = mapping.get(raw_field)[0]
        field_name = mapping.get(raw_field)[1]
        # _log.debug("item is in the mapping: %s -- %s" % (table_name, field_name))

        if is_extra_data:
            if hasattr(model, 'extra_data'):
                # only save it if the model and the mapping are the same
                if model.__class__.__name__ == table_name:
                    model.extra_data[raw_field] = cleaned_value
                else:
                    _log.debug(
                        "model name (%s) is not the same as the mapped table name (%s) -- skipping" % (
                        model.__class__.__name__, table_name))  # noqa
            else:
                _log.debug(
                    "model object does not have extra_data field, skipping mapping for %s" % raw_field)  # noqa
        else:
            # Simply set the field to the cleaned value
            setattr(model, field_name, cleaned_value)

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


def map_row(row, mapping, model_class, extra_data_fields=[], cleaner=None, concat=None, **kwargs):
    """Apply mapping of row data to model.

    :param row: dict, parsed row data from csv.
    :param mapping: dict, keys map row columns to model_class attrs.
    :param model_class: class, reference to model class we map against.
    :param extra_data_fields: list, list of raw columns that are considered extra data (per mapping)
    :param cleaner: (optional) inst, cleaner instance for row values.
    :param concat: (optional) list of dict,
        config for concatenating rows into an attr.
    :rtype: model_inst, with mapped data attributes; ready to save.

    """
    initial_data = kwargs.get('initial_data', None)
    model = model_class()

    # If there are any initial states we need to set prior to mapping.
    if initial_data:
        model = apply_initial_data(model, initial_data)

    # concat is not used as of 2016-09-14
    # concat = _set_default_concat_config(concat)

    # In case we need to look up cleaner by dynamic field mapping.
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
