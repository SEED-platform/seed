# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.core.cache import cache as django_cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT


def make_key(key):
    return unicode(django_cache.make_key(key))


def set_cache_raw(key, data, timeout=DEFAULT_TIMEOUT):
    django_cache.set(key, data, timeout)


def get_cache_raw(key, default=None):
    return django_cache.get(key, default)


def set_cache(progress_key, status, data):
    """
    Sets the cache key to a pickled dictionary containing at least status and progress.
    If data is not a dict, it is assumed to be a progress percentage.
    """
    if not isinstance(status, str):
        raise ValueError('Invalid value for status; must be a string')

    result = {}
    if not isinstance(data, dict):
        result['progress'] = data
    else:
        result = data
    result['status'] = status
    set_cache_raw(progress_key, result, DEFAULT_TIMEOUT)

    return result


def get_cache(progress_key, default=None):
    """Unpickles the cache key to a dictionary and resets the timeout"""
    if default is not None:
        if not isinstance(default, dict):
            default = {'status': 'Unknown', 'progress': default}
    data = get_cache_raw(progress_key, default)
    if data is None:
        # Cache accessed before it was created
        data = {'status': 'parsing', 'progress': 0.0}
    else:
        # Set cache to same value to reset timeout
        set_cache(progress_key, data['status'], data)
    return data


def set_cache_state(progress_key, state):
    """Sets the cache key or progress_key to a bool."""
    if not isinstance(state, bool):
        raise ValueError('Invalid value for state; must be a bool')

    result = state
    set_cache_raw(progress_key, result, DEFAULT_TIMEOUT)

    return result


def get_cache_state(progress_key, default=None):
    """Gets the state of progress_key"""
    if default is not None:
        if not isinstance(default, bool):
            raise ValueError('Invalid value for default; must be a bool')
    data = get_cache_raw(progress_key, default)
    return data


def delete_cache(progress_key):
    """Delete the cache associated with the progress_key"""
    django_cache.delete(progress_key)


def lock_cache(progress_key, timeout=60):
    """Set the lock with a default timeout of 1 minute"""
    set_cache_raw(progress_key, 1, timeout)


def unlock_cache(progress_key, timeout=DEFAULT_TIMEOUT):
    """Unset the lock"""
    set_cache_raw(progress_key, 0, timeout)


def get_lock(lock_key, default=0):
    """Return the locked status. If the lock key does not exist, return 0"""
    return get_cache_raw(lock_key, default)


def increment_cache(key, increment):
    """Increment cache by value increment, never exceed 100."""
    increment = round(increment, 2)
    value = get_cache(key)
    value = float(value['progress'])
    if value + increment >= 100.0:
        value = 100.0
    else:
        value += increment

    set_cache(key, 'parsing', value)
    return {'status': 'parsing', 'progress': value}


def clear_cache():
    django_cache.clear()
