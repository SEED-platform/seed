"""
:copyright: (c) 2014 Building Energy Inc
"""
import json

from mcm import matchers
from mcm.cleaners import default_cleaner


def build_column_mapping(
    raw_columns,
    dest_columns,
    previous_mapping=None,
    map_args=None,
    thresh=None
):
    """Build a probabalistic mapping structure for mapping raw to dest.

    :param raw_columns: list of str. The column names we're trying to map.
    :param dest_columns: list of str. The columns we're mapping to.
    :param previous_mapping: callable. Used to return the previous mapping
        for a given field.

        Example:
        ``
        # The expectation is that our callable always gets passed a
        # raw key. If it finds a match, it returns the raw_column and score.
        previous_mapping('example field', *map_args) ->
            ('field_1', 0.93)
        ``

    :returns dict: {'raw_column': [('dest_column', score)...],...}

    """
    probable_mapping = {}
    thresh = thresh or 0
    for raw in raw_columns:
        result = []
        conf = 0
        # We want previous mappings to be at the top of the list.
        if previous_mapping and callable(previous_mapping):
            args = map_args or []
            mapping = previous_mapping(raw, *args)
            if mapping:
                result, conf = mapping

        # Only enter this flow if we haven't already selected a result.
        if not result and result is not None:
            best_match, conf = matchers.best_match(
                raw, dest_columns, top_n=1
            )[0]
            if conf > thresh:
                result = best_match
            else:
                result = None
                conf = 0

        probable_mapping[raw] = [result, conf]

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
        elif (
            hasattr(model, 'extra_data') and isinstance(model.extra_data, dict)
        ):
            model.extra_data[item] = value

    return model


def _concat_values(concat_columns, column_values, delimiter):
    """Concatenate the values into one string to set for target."""
    # Use the order of values that we got from concat_columns def.
    values = [
        column_values[item] for item in concat_columns if item in column_values
    ]
    return delimiter.join(values) or None


def apply_column_value(item, value, model, mapping, cleaner, apply_func=None):
    """Set the column value as the target attr on our model.

    :param item: str, the column name as the mapping understands it.
    :param value: dict, the value of that column for a given row.
    :param model: inst, the object we're mapping data to.
    :param mapping: dict, the mapping of row data to attribute data.
    :param cleaner: runnable, something to clean data values.
    :param apply: (optional), function to apply value to our model.
    :rtype: model inst

    """
    column_name = item
    if cleaner:
        if item not in (cleaner.float_columns or cleaner.date_columns):
            # Try using a reverse mapping for dynamic maps;
            # default to row name if it's not mapped
            column_name = mapping.get(item, column_name)

        cleaned_value = cleaner.clean_value(value, column_name)
    else:
        cleaned_value = default_cleaner(value)
    if item in mapping:
        if apply_func and callable(apply_func):
            # If we need to call a function to apply our value, do so.
            # We use the 'mapped' name of the column, and the cleaned value.
            apply_func(model, mapping.get(item), cleaned_value)
        else:
            setattr(model, mapping.get(item), cleaned_value)
    elif hasattr(model, 'extra_data'):
        if not isinstance(model.extra_data, dict):
            # sometimes our dict is returned as JSON string.
            # TODO: Need to resolve this upstream with djorm-ext-jsonfield.
            model.extra_data = json.loads(model.extra_data)
        model.extra_data[item] = cleaned_value
    else:
        model.extra_data = {item: cleaned_value}

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


def map_row(row, mapping, model_class, cleaner=None, concat=None, **kwargs):
    """Apply mapping of row data to model.

    :param row: dict, parsed row data from csv.
    :param mapping: dict, keys map row columns to model_class attrs.
    :param model_class: class, reference to model class we map against.
    :param cleaner: (optional) inst, cleaner instance for row values.
    :param concat: (optional) list of dict,
        config for concatenating rows into an attr.
    :rtype: model_inst, with mapped data attributes; ready to save.

    """
    initial_data = kwargs.get('initial_data', None)
    apply_columns = kwargs.get('apply_columns', [])
    apply_func = kwargs.get('apply_func', None)
    model = model_class()
    # If there are any initial states we need to set prior to mapping.
    if initial_data:
        model = apply_initial_data(model, initial_data)

    concat = _set_default_concat_config(concat)

    # In case we need to look up cleaner by dynamic field mapping.
    for item, value in row.items():
        # Look through any of our concatenation configs to see if this row
        # needs to be set aside for mergning with others at the end of the map.
        for concat_column in concat:
            if item in concat_column['concat_columns']:
                concat_column['concat_values'][item] = value
                continue

        # If our item is a column which requires that we apply the function
        # then, send_apply_func will reference this function and be sent
        # to the ``apply_column_value`` function.
        send_apply_func = apply_func if item in apply_columns else None
        if value and value != '':
            model = apply_column_value(
                item, value, model, mapping, cleaner,
                apply_func=send_apply_func
            )

    if concat and [c['concat_values'] for c in concat]:
        # We've skipped mapping any columns which we're going to concat.
        # Now we concatenate them all and save to their designated target.
        for c in concat:
            mapping[c['target']] = c['target']
            concated_vals = _concat_values(
                c['concat_columns'],
                c['concat_values'],
                c['delimiter']
            )
            model = apply_column_value(
                c['target'],
                concated_vals,
                model,
                mapping,
                cleaner,
                apply_func=apply_func,
            )

    return model
