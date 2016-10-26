# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import copy
import logging
import re

import matchers
from cleaners import default_cleaner

_log = logging.getLogger(__name__)


def build_column_mapping(raw_columns, dest_columns, previous_mapping=None, map_args=None, thresh=0):
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


    mappings = []
    for raw in raw_columns:
        attempt_best_match = False
        # We want previous mappings to be at the top of the list.
        if previous_mapping and callable(previous_mapping):
            args = map_args or []
            mapping = previous_mapping(raw, *args)  # Mapping will look something like this -- [u'', u'', 100]
            if mapping:
                mappings.append((raw, True, mapping))
            else:
                attempt_best_match = True
        else:
            attempt_best_match = True

        # Only enter this flow if we haven't already selected a result. Ignore blank columns with
        # conf of 100 since a conf of 100 signifies the user has saved that mapping.
        if attempt_best_match:
            # convert raw fields spaces into underscores because that is what is in the database
            raw_test = raw.replace(' ', '_')

            # try some alternatives to the raw column in specific cases (e.g. zip => postal code).
            # Hack for now, but should make this some global config or organization specific
            # config
            if raw_test.lower() == 'zip':
                raw_test = 'postal_code'
            if raw_test.lower() == 'gba':
                raw_test = 'gross_floor_area'

            # go get the top 5 matches. format will be [('PropertyState', 'building_count', 62), ...]

            matches = matchers.best_match(raw_test, dest_columns, top_n=5)

            mappings.append((raw, False, matches))


    # Go through the mappings and figure out if there are any duplicates, if so, then pick the duplicate that has the
    # next highest confidence. previous mappings that are 100% are set in the confident mapping as True because other
    # mapping may be 100%, but not confident, weee!
    probable_mapping = {}
    for mapping in mappings:
        probable_mapping[mapping[0]] = list(mapping[2][0])



        # table, best_match, conf =


        # if conf > thresh:
        #     result = best_match
        #     result_table = table
        # else:
        #     result = None
        #     conf = 0


        # probable_mapping[raw] = [result_table, result, conf]

    print mappings
    print probable_mapping
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


def expand_field(field):
    """
    take a field from the csv and expand/split on a delimiter and return a list of individual values

    :param field: str, value to parse

    :return: list of individual values after after delimiting
    """

    if isinstance(field, str) or isinstance(field, unicode):
        return [r.strip() for r in re.split(",|;|:", field)]
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
