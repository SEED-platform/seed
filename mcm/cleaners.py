"""
:copyright: (c) 2014 Building Energy Inc
"""
import dateutil
from datetime import datetime, date
import re
import string

from mcm.matchers import fuzzy_in_set


NONE_SYNONYMS = (u'not available', u'not applicable', u'n/a')
BOOL_SYNONYMS = (u'true', u'yes', u'y', u'1')
PUNCT_REGEX = re.compile('[{0}]'.format(
    re.escape(string.punctuation.replace('.', '')))
)


def default_cleaner(value, *args):
    """Pass-through validation for strings we don't know about."""
    if isinstance(value, unicode):
        if fuzzy_in_set(value.lower(), NONE_SYNONYMS):
            return None
    return value


def float_cleaner(value, *args):
    """Try to clean value, coerce it into a float."""
    if not value:
        return None
    if isinstance(value, float) or isinstance(value, int):
        return float(value)
    try:
        value = PUNCT_REGEX.sub('', value)
        value = float(value)
    except ValueError:
        return None

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
    if not value:
        return None
    if isinstance(value, datetime) or isinstance(value, date):
        return value
    try:
        dateutil.parser.parse(value)
    except (TypeError, ValueError):
        return None

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
            lambda x: self.schema[x] == u'date', self.schema
        )

    def clean_value(self, value, column_name):
        """Clean the value, based on characteristics of its column_name."""
        value = default_cleaner(value)
        if column_name in self.float_columns:
            return float_cleaner(value)

        if column_name in self.date_columns:
            return date_cleaner(value)

        return value
