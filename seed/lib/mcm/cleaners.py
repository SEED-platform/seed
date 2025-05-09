"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import re
import string
import unicodedata
from datetime import date, datetime

import dateutil
import dateutil.parser
from django.contrib.gis.geos import GEOSGeometry
from django.utils import timezone

# django orm gets confused unless we specifically use `ureg` from quantityfield
# ie. don't try `import pint; ureg = pint.UnitRegistry()`
from quantityfield.units import ureg

from seed.lib.mcm.matchers import fuzzy_in_set

NONE_SYNONYMS = (
    ("_", "not available"),
    ("_", "not applicable"),
    ("_", "n/a"),
)
BOOL_SYNONYMS = (
    ("_", "true"),
    ("_", "yes"),
    ("_", "y"),
    ("_", "1"),
)
PUNCT_REGEX = re.compile(f"[{re.escape(string.punctuation.replace('.', '').replace('-', ''))}]")
# Mapping of specific characters to their normalized versions (need to expand this list)
CHAR_MAPPING = {
    ord("“"): '"',
    ord("”"): '"',
    ord("‘"): "'",  # noqa: RUF001
    ord("’"): "'",  # noqa: RUF001
    ord("′"): "'",  # noqa: RUF001
    ord("″"): '"',
    ord("‴"): "'''",
    ord("…"): "...",
    ord("•"): "*",
    ord("⁄"): "/",  # noqa: RUF001
    ord("×"): "x",  # noqa: RUF001
    ord("⁓"): "~",  # noqa: RUF001
    # mdash, ndash, horizontal bar
    ord("–"): "-",  # noqa: RUF001
    ord("—"): "--",
    ord("―"): "-",
    ord("¬"): "-",
    # guillemets to single and double quotes
    ord("‹"): '"',  # noqa: RUF001
    ord("›"): '"',  # noqa: RUF001
    ord("«"): '"',
    ord("»"): '"',
}


def normalize_unicode_and_characters(text):
    """Method to normalize unicode characters and replace specific characters with their normalized versions."""
    # Normalize Unicode characters to their canonical form (NFC decomposition) --
    # Combines characters and diacritics when possible.

    # Unicode standardizes on a single code point for accented characters such as é, ü, and ñ.
    # More info can be seed here: https://docs.python.org/2/library/unicodedata.html#unicodedata.normalize
    normalized_text = unicodedata.normalize("NFC", text)

    # Apply CHAR_MAPPINGS to remove certain characters to be normalized.
    normalized_text = normalized_text.translate(CHAR_MAPPING)

    return normalized_text


def default_cleaner(value, *args):
    """Pass-through validation for strings we don't know about."""
    if isinstance(value, str):
        if fuzzy_in_set(value.lower(), NONE_SYNONYMS):
            return None
        # guard against `''` coming in from an Excel empty cell
        if value == "":
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
    # If this is a unit field, then just return it as is
    if isinstance(value, ureg.Quantity):
        return value

    # API breakage if None does not return None
    if value is None:
        return None

    if isinstance(value, str):
        value = PUNCT_REGEX.sub("", value)

    try:
        value = float(value)
    except ValueError:
        value = None
    except TypeError:
        message = f"float_cleaner cannot convert {type(value)} to float"
        raise TypeError(message)

    return value


def enum_cleaner(value, choices, *args):
    """Do we exist in the set of enum values?"""
    return fuzzy_in_set(value, choices) or None


def bool_cleaner(value, *args):
    if isinstance(value, bool):
        return value

    return fuzzy_in_set(value.strip().lower(), BOOL_SYNONYMS)


def date_time_cleaner(value, *args):
    """Try to clean value, coerce it into a python datetime."""
    if not value or value == "":
        return None
    if isinstance(value, (datetime, date)):
        return value

    try:
        # the dateutil parser only parses strings, make sure to return None if not a string
        if isinstance(value, str):
            value = dateutil.parser.parse(value)
            value = timezone.make_aware(value, timezone.get_current_timezone())
        else:
            value = None
    except (TypeError, ValueError):
        return None

    return value


def date_cleaner(value, *args):
    """Try to clean value, coerce it into a python datetime, then call .date()"""
    value = date_time_cleaner(value)
    if value:
        return value.date()
    else:
        return None


def int_cleaner(value, *args):
    """Try to convert to an integer"""
    # API breakage if None does not return None
    if value is None:
        return None

    if isinstance(value, str):
        value = PUNCT_REGEX.sub("", value)

    try:
        value = int(float(value))
    except ValueError:
        value = None
    except TypeError:
        message = f"int_cleaner cannot convert {type(value)} to int"
        raise TypeError(message)

    return value


def pint_cleaner(value, units, *args):
    """Try to convert value to a meaningful (magnitude, units) object."""

    # If value is already a Quantity don't multiply the units
    if isinstance(value, ureg.Quantity):
        return value

    value = float_cleaner(value)
    # API breakage if None does not return None
    if value is None:
        return None

    try:
        value = value * ureg(units)
    except ValueError:
        value = None
    except TypeError:
        message = f"pint_cleaner cannot convert {type(value)} to a valid Quantity"
        raise TypeError(message)

    return value


def geometry_cleaner(value):
    try:
        return GEOSGeometry(value, srid=4326)
    except ValueError as e:
        if "String or unicode input unrecognized as WKT EWKT, and HEXEWKB." in str(e):
            return None
    except TypeError as e:
        if "Improper geometry input type" in str(e):
            return None


class Cleaner:
    """Cleans values for a given ontology."""

    def __init__(self, ontology):
        self.ontology = ontology
        self.schema = self.ontology.get("types", {})
        self.float_columns = list(filter(lambda x: self.schema[x] == "float", self.schema))
        self.date_columns = list(filter(lambda x: self.schema[x] == "date", self.schema))
        self.date_time_columns = list(filter(lambda x: self.schema[x] == "datetime", self.schema))
        self.string_columns = list(filter(lambda x: self.schema[x] == "string", self.schema))
        self.int_columns = list(filter(lambda x: self.schema[x] == "integer", self.schema))
        self.geometry_columns = list(filter(lambda x: self.schema[x] == "geometry", self.schema))
        self.pint_column_map = self._build_pint_column_map()

    def _build_pint_column_map(self):
        """
        The schema contains { raw_column_name: ('quantity', UNIT_STRING) }
        tuples to define a pint mapping.
        Returns a dict { raw_column_name: UNIT_STRING) } to make it simple to check
        if it's a pint column (checking against `keys()`) and to get the units for
        use with `pint_cleaner(value, UNIT_STRING)`

        example input: {
            'pm_parent_property_id': 'string',
            'Weather Normalized Site EUI (GJ/m2)': ('quantity', 'GJ/m**2/year')
        }

        example output: {
            'Weather Normalized Site EUI (GJ/m2)': 'GJ/m**2/year'
        }
        """
        pint_column_map = {
            raw_col: pint_spec[1]
            for (raw_col, pint_spec) in self.schema.items()
            if isinstance(pint_spec, tuple) and pint_spec[0] == "quantity"
        }

        return pint_column_map

    def clean_value(self, value, column_name, is_extra_data=True):
        """Clean the value, based on characteristics of its column_name."""
        value = default_cleaner(value)
        if value is not None:
            if column_name in self.float_columns:
                return float_cleaner(value)

            if column_name in self.date_time_columns:
                return date_time_cleaner(value)

            if column_name in self.date_columns:
                return date_cleaner(value)

            if column_name in self.string_columns:
                return str(value)

            if column_name in self.int_columns:
                return int_cleaner(value)

            if column_name in self.geometry_columns:
                return geometry_cleaner(value)

            # If the object is not extra data, then check if the data are in the
            # pint_column_map. This needs to be cleaned up significantly.
            if not is_extra_data and column_name in self.pint_column_map:
                units = self.pint_column_map[column_name]
                return pint_cleaner(value, units)

        return value
