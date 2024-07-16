# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from typing import Optional, Union

from django.core.cache import cache as django_cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT


def make_key(key: str):
    return str(django_cache.make_key(key))


def set_cache_raw(key: str, data, timeout=DEFAULT_TIMEOUT):
    django_cache.set(key, data, timeout)


def get_cache_raw(key: str, default=None):
    return django_cache.get(key, default)


def set_cache(progress_key: str, status: str, data: Union[dict, int]) -> dict:
    """
    Sets the cache key to a pickled dictionary containing at least status and progress.
    If data is not a dict, it is assumed to be a progress percentage.
    """
    if not isinstance(status, str):
        raise ValueError("Invalid value for status; must be a string")

    result = {}
    if not isinstance(data, dict):
        result["progress"] = data
    else:
        result = data
    result["status"] = status
    set_cache_raw(progress_key, result)

    return result


def get_cache(progress_key: str, default: Optional[Union[dict, int, float]] = None) -> dict:
    """Unpickles the cache key to a dictionary and resets the timeout"""
    if default is not None and not isinstance(default, dict):
        default = {"status": "Unknown", "progress": default}
    data = get_cache_raw(progress_key, default)
    if data is None:
        # Cache accessed before it was created
        data = {"status": "pending", "progress": 0}
    else:
        # Reset the key's expiration
        touch(progress_key)
    return data


def touch(key: str) -> None:
    # Reset the key's expiration
    django_cache.touch(key)


def increment_progress(progress_key: str, delta: int = 1) -> None:
    """Atomically increments the completed progress of a progress_key"""
    completed_key = f"{progress_key}:COMPLETED"
    django_cache.incr(completed_key, delta)

    # Reset the keys' expirations
    touch(progress_key)
    touch(completed_key)


def set_cache_state(state_key: str, state: bool) -> None:
    """Sets the state_key to a bool."""
    if not isinstance(state, bool):
        raise ValueError("Invalid value for state; must be a bool")

    set_cache_raw(state_key, state)


def get_cache_state(state_key: str, default: Optional[bool] = None) -> bool:
    """Gets the state of state_key"""
    if default is not None and not isinstance(default, bool):
        raise ValueError("Invalid value for default; must be a bool")
    return bool(get_cache_raw(state_key, default))


def delete_cache(key: str) -> None:
    """Delete the cache associated with the progress_key"""
    django_cache.delete(key)


def lock_cache(lock_key: str, timeout=60) -> None:
    """Set the lock with a default timeout of 1 minute"""
    set_cache_raw(lock_key, True, timeout)


def unlock_cache(lock_key: str) -> None:
    """Unset the lock"""
    delete_cache(lock_key)


def is_locked(lock_key: str) -> bool:
    """Return the locked status. If the lock key does not exist, return False"""
    return bool(get_cache_raw(lock_key))


def clear_cache():
    django_cache.clear()
