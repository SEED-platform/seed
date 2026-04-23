"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import calendar
import datetime

import dateutil
import pytz
from django.utils.timezone import make_aware


def convert_datestr(datestr, make_tz_aware=False):
    """
    Converts dates like `12/31/2010` into datetime objects. Dates are returned in UTC time

    TODO: reconcile this with seed/lib/mcm/cleaners.py#L85-L85

    :param datestr: string, value to convert
    :param make_tz_aware: bool, if set to true, then will convert the timezone into UTC time
    :return: datetime or None
    """
    try:
        value = dateutil.parser.parse(datestr)
        if make_tz_aware:
            value = make_aware(value, pytz.UTC)
        return value
    except (TypeError, ValueError):
        return None


def convert_to_js_timestamp(timestamp):
    """converts a django/python datetime object to milliseconds since epoch"""
    if timestamp:
        return calendar.timegm(timestamp.timetuple()) * 1000
    return None


def parse_datetime(maybe_datetime):
    """
    Process a datetime value that may be None, timestamp, strftime.
    """
    if isinstance(maybe_datetime, (int, float)):
        return datetime.datetime.fromtimestamp(maybe_datetime / 1000)
    elif isinstance(maybe_datetime, str):
        return dateutil.parser.parse(maybe_datetime)
    else:
        return None


def localize_datetime(value, tz, is_dst=None):
    """
    Convert a naive datetime to an aware datetime without relying on Django's
    deprecated ``is_dst`` passthrough.

    ``pytz`` timezones support ``localize`` for DST disambiguation. For other
    timezone implementations, fall back to Django's ``make_aware``.
    """
    if hasattr(tz, "localize"):
        return tz.localize(value, is_dst=is_dst)

    if is_dst is not None:
        raise ValueError("is_dst can only be used with pytz timezones")

    return make_aware(value, timezone=tz)


def localize_datetime_with_dst_fallbacks(value, tz):
    """
    Localize a naive datetime while preserving the historical SEED behavior for
    ambiguous and nonexistent timestamps around DST transitions.
    """
    try:
        return localize_datetime(value, tz)
    except pytz.AmbiguousTimeError:
        return localize_datetime(value, tz, is_dst=False)
    except pytz.NonExistentTimeError:
        return localize_datetime(value, tz, is_dst=True)
