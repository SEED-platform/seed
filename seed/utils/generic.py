# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import json
import logging
import math
from datetime import datetime

from django.core import serializers
from django.contrib.postgres.fields import JSONField


class MarkdownPackageDebugFilter(logging.Filter):
    def filter(self, record):
        if 'markdown.extensions.headerid' in record.msg:
            return False
        return True


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


def obj_to_dict(obj, include_m2m=True):
    """
    serializes obj for a JSON friendly version tries to serialize JSONField
    """
    # http://www.django-rest-framework.org/api-guide/fields/#jsonfield
    if include_m2m:
        data = serializers.serialize('json', [obj, ])
    else:
        data = serializers.serialize('json', [obj, ], fields=tuple(
            [f.name for f in obj.__class__._meta.local_fields]
        ))

    struct = json.loads(data)[0]
    response = struct['fields']
    response[u'id'] = response[u'pk'] = struct['pk']
    response[u'model'] = struct['model']
    # JSONField does not get serialized by `serialize`
    for f in obj._meta.fields:
        if isinstance(f, JSONField):
            e = getattr(obj, f.name)
            # PostgreSQL < 9.3 support -- this should never be run
            while isinstance(e, unicode):
                e = json.loads(e)
            response[unicode(f.name)] = e
    return response


def pp(model_obj):
    """
    Pretty Print the model object
    """

    data = serializers.serialize('json', [model_obj, ])
    # from django.forms.models import model_to_dict
    # j = model_to_dict(model_obj)
    print json.dumps(json.loads(data), indent=2)


def json_serializer(obj):
    """
    Serialize JSON with date times. When using json.dumps use call it with:

    import json
    from seed.utils.generic import json_serializer
    json.dumps(data, default=json_serializer, indent=2)
    """
    if isinstance(obj, datetime):
        serial = obj.isoformat()
        return serial
