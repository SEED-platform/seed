# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import dateutil


def convert_datestr(datestr):
    """Converts dates like `12/31/2010` into datetime objects."""
    try:
        return dateutil.parser.parse(datestr)
    except (TypeError, ValueError):
        return None


def convert_to_js_timestamp(timestamp):
    """converts a django/python datetime object to milliseconds since epoch"""
    if timestamp:
        return int(timestamp.strftime("%s")) * 1000
    return None
