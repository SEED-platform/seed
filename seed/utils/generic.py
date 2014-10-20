"""
:copyright: (c) 2014 Building Energy Inc
"""


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
