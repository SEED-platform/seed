# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""
import logging

_log = logging.getLogger(__name__)


def api_success(**kwargs):
    """JSON response for API success.
    """
    d = {'success': True}
    d.update(kwargs)
    return d


def api_error(reason):
    """JSON response for API error.
    """
    return {'success': False, 'reason': reason}


def missing_request_keys(keys, body):
    """Check for `keys` in `body`.

    Args:
        keys (list): List of keys to check
        body (dict): body of request
    Returns:
       None if all present, JSON error response (using `api_error()`)
       if one or more is missing.
    """
    missing = [k for k in keys if k not in body]
    if not missing:
        return None
    msg = "Required key{} '{}' is missing".format(
        's' if len(missing) > 1 else '', ','.join(missing))
    _log.warn("returning input error: {}".format(msg))
    return msg


def typeof_request_values(types, body):
    """Check for type of request values.

    Pre:
        All keys in types are present in body.
    Args:
        types (dict): key to type map, where `type` is a function
            used to test the type conversion. It should take one argument,
            the value, and raise a ValueError if it is invalid.
        body (dict): body of request
    Returns:
        None if all OK, JSON error response (using `api_error()`)
       if one or more is of the wrong type.
    """
    bad = []
    for k in types:
        try:
            types[k](body[k])  # convert
        except ValueError:
            bad.append(k)
    if not bad:
        return None
    msg = "Values for key{} are of the wrong type. Expected: ({})"
    plural = 's' if len(bad) > 1 else ''
    what_is_bad = ','.join(["{} => {}".format(key, val)
                            for key, val in types.items()])
    msg = msg.format(plural, what_is_bad)
    _log.warn("returning input error: {}".format(msg))
    return msg
