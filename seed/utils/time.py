# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import calendar
import datetime

import dateutil
import pytz
from django.utils.timezone import make_aware
from past.builtins import basestring


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
    elif isinstance(maybe_datetime, basestring):
        return dateutil.parser.parse(maybe_datetime)
    else:
        return None
