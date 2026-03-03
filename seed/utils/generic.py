"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import json
import logging
import math
import re
from contextlib import suppress
from datetime import datetime

from django.core import serializers
from django.db import IntegrityError, models
from django.utils import timezone
from pint import UnitRegistry

ureg = UnitRegistry()
Quantity = ureg.Quantity


class MarkdownPackageDebugFilter(logging.Filter):
    def filter(self, record):
        return "markdown.extensions.headerid" not in record.msg


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
    # ensure list of not a bunch of "None"
    if set(lst) == {None}:
        return
    index = (len(lst) - 1) // 2
    if len(lst) % 2:
        return sorted(lst)[index]
    return (sorted(lst)[index] + sorted(lst)[index + 1]) / 2.0


def round_down_hundred_thousand(x):
    return math.floor(x / 100000.0) * 100000


def obj_to_dict(obj, include_m2m=True):
    """
    serializes obj for a JSON friendly version tries to serialize JSONField
    """
    # http://www.django-rest-framework.org/api-guide/fields/#jsonfield
    if include_m2m:
        data = serializers.serialize(
            "json",
            [
                obj,
            ],
        )
    else:
        data = serializers.serialize(
            "json",
            [
                obj,
            ],
            fields=tuple([f.name for f in obj.__class__._meta.local_fields]),
        )

    struct = json.loads(data)[0]
    response = struct["fields"]
    response["id"] = response["pk"] = struct["pk"]
    response["model"] = struct["model"]
    # JSONField does not get serialized by `serialize`
    # TODO: I think django can now serialize JSONFields
    for f in obj._meta.fields:
        if isinstance(f, models.JSONField):
            e = getattr(obj, f.name)
            # PostgreSQL < 9.3 support -- this should never be run
            while isinstance(e, str):
                e = json.loads(e)
            response[str(f.name)] = e
    return response


def pp(model_obj):
    """
    Pretty Print the model object
    """

    data = serializers.serialize(
        "json",
        [
            model_obj,
        ],
    )
    # from django.forms.models import model_to_dict
    # j = model_to_dict(model_obj)
    print(json.dumps(json.loads(data), indent=2))


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


def compare_orgs_between_label_and_target(sender, pk_set, instance, model, action, **kwargs):
    for id in pk_set:
        label = model.objects.get(pk=id)
        if instance.cycle.organization.get_parent().id != label.super_organization_id:
            raise IntegrityError(
                f"Label with super_organization_id={label.super_organization_id} cannot be applied to a record with parent "
                f"organization_id={instance.cycle.organization.get_parent().id}."
            )


def get_int(value, default=None):
    if isinstance(value, Quantity):
        value = value.magnitude
    try:
        result = int(float(value))
        return result if result > 0 else default
    except (ValueError, TypeError):
        return default


def parse_date(value):
    """
    Parse a date string and return it as an aware datetime object.

    Supports partial ISO and US date formats:
     - YYYY
     - YYYY-MM
     - YYYY-MM-DD
     - YYYY-MM-DD HH:MM:SS
     - YYYY-MM-DDTHH:MM:SS
     - MM-DD-YYYY
     - MM-DD-YY

    '-' and '/' are interchangeable separators.
    Optional comparison operators (=, !=, <, <=, >, >=) can prefix the date.

    """
    if not value:
        return timezone.make_aware(datetime.min)

    # standardize separators, ignore optional operators
    s = str(value).strip().replace("/", "-")
    match = re.match(r"^(=|!=|<=|>=|<|>)\s*(.+)$", s)
    if match:
        s = match.group(2)

    # ISO/Partial ISO Format
    with suppress(ValueError, TypeError):
        return timezone.make_aware(datetime.fromisoformat(s))

    if re.fullmatch(r"\d{4}", s):  # YYYY
        return timezone.make_aware(datetime(int(s), 1, 1))

    if re.fullmatch(r"\d{4}[-]\d{1,2}", s):  # YYYY-MM
        year, month = map(int, re.split(r"[-]", s))
        return timezone.make_aware(datetime(year, month, 1))

    if re.fullmatch(r"\d{4}[-]\d{1,2}[-]\d{1,2}", s):  # YYYY-MM-DD
        year, month, day = map(int, re.split(r"[-]", s))
        return timezone.make_aware(datetime(year, month, day))

    # US-style:
    with suppress(ValueError):
        return timezone.make_aware(datetime.strptime(s, "%m-%d-%Y"))  # MM-DD-YYYY

    with suppress(ValueError):
        return timezone.make_aware(datetime.strptime(s, "%m-%d-%y"))  # MM-DD-YY

    raise ValueError(f'Unable to parse date from value "{value}".')
