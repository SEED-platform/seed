# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import re
import string
from datetime import datetime, date

import dateutil
import dateutil.parser
from django.utils import timezone

from seed.lib.mcm.matchers import fuzzy_in_set

NONE_SYNONYMS = (
    (u'_', u'not available'),
    (u'_', u'not applicable'),
    (u'_', u'n/a'),
)
BOOL_SYNONYMS = (
    (u'_', u'true'),
    (u'_', u'yes'),
    (u'_', u'y'),
    (u'_', u'1'),
)
PUNCT_REGEX = re.compile('[{0}]'.format(
    re.escape(string.punctuation.replace('.', '').replace('-', '')))
)


def default_cleaner(value, *args):
    """Pass-through validation for strings we don't know about."""
    if isinstance(value, unicode):
        if fuzzy_in_set(value.lower(), NONE_SYNONYMS):
            return None
    return value


def float_cleaner(value, *args):
    """Try to clean value, coerce it into a float.
    Usage:
        float_cleaner('1,123.45')       # 1123.45
        float_cleaner('1,123.45 ?')     # 1123.45
        float_cleaner(50)               # 50.0
        float_cleaner(-55)              # -55.0
        float_cleaner(None)             # None
        float_cleaner(Decimal('30.1'))  # 30.1
        float_cleaner(my_date)          # raises TypeError
    """
    # API breakage if None does not return None
    if value is None:
        return None

    if isinstance(value, (str, unicode)):
        value = PUNCT_REGEX.sub('', value)

    try:
        value = float(value)
    except ValueError:
        value = None
    except TypeError:
        message = 'float_cleaner cannot convert {} to float'.format(type(value))
        raise TypeError(message)

    return value


def enum_cleaner(value, choices, *args):
    """Do we exist in the set of enum values?"""
    return fuzzy_in_set(value, choices) or None


def bool_cleaner(value, *args):
    if isinstance(value, bool):
        return value

    if fuzzy_in_set(value.strip().lower(), BOOL_SYNONYMS):
        return True
    else:
        return False


def date_cleaner(value, *args):
    """Try to clean value, coerce it into a python datetime."""
    if not value or value == '':
        return None
    if isinstance(value, (datetime, date)):
        return value

    try:
        # the dateutil parser only parses strings, make sure to return None if not a string
        if isinstance(value, (str, unicode)):
            value = dateutil.parser.parse(value)
            value = timezone.make_aware(value, timezone.get_current_timezone())
        else:
            value = None
    except (TypeError, ValueError):
        return None

    return value


def int_cleaner(value, *args):
    """Try to convert to an integer"""
    # API breakage if None does not return None
    if value is None:
        return None

    if isinstance(value, (str, unicode)):
        value = PUNCT_REGEX.sub('', value)

    try:
        value = int(float(value))
    except ValueError:
        value = None
    except TypeError:
        message = 'int_cleaner cannot convert {} to int'.format(type(value))
        raise TypeError(message)

    return value


class Cleaner(object):
    """Cleans values for a given ontology."""

    def __init__(self, ontology):

        self.ontology = ontology
        self.schema = self.ontology.get(u'types', {})
        self.float_columns = filter(
            lambda x: self.schema[x] == u'float', self.schema
        )
        self.date_columns = filter(
            lambda x: self.schema[x] == u'date' or self.schema[x] == u'datetime', self.schema
        )
        self.string_columns = filter(
            lambda x: self.schema[x] == u'string', self.schema
        )
        self.int_columns = filter(
            lambda x: self.schema[x] == u'integer', self.schema
        )

    def clean_value(self, value, column_name):
        """Clean the value, based on characteristics of its column_name."""
        value = default_cleaner(value)
        if value is not None:
            if column_name in self.float_columns:
                return float_cleaner(value)

            if column_name in self.date_columns:
                return date_cleaner(value)

            if column_name in self.string_columns:
                return str(value)

            if column_name in self.int_columns:
                return int_cleaner(value)

        return value
