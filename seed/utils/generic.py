"""
:copyright: (c) 2014 Building Energy Inc
"""
import math

def split_model_fields(obj, fields):
    """
    Takes a Python object and a list of field names.

    Returns (attr_fields, non_attr_fields,) where attr_fields are the
    fields for which hasattr(obj, field) returns True, and where
    non_attr_fields are the fields for which hasattr(obj, field returns
    False.
    """
    model_fields = []
    other_fields = []

    for field in fields:
        if hasattr(obj, field):
            model_fields.append(field)
        else:
            other_fields.append(field)

    return model_fields, other_fields


def median(lst):
    if not lst:
        return
    index = (len(lst) - 1) // 2
    if (len(lst) % 2):
        return sorted(lst)[index]
    return (sorted(lst)[index] + sorted(lst)[index + 1]) / 2.0


def round_down_hundred_thousand(x):
    return int(math.floor(x / 100000.0)) * 100000
