from django.core.cache import cache as django_cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT


def make_key(key):
    return unicode(django_cache.make_key(key))


def set_cache_raw(progress_key, data, timeout=DEFAULT_TIMEOUT):
    django_cache.set(progress_key, data, timeout)


def get_cache_raw(progress_key):
    return django_cache.get(progress_key)


def set_cache(progress_key, status, data):
    """Sets the cache key to a pickled dictionary containing at least status and progress. If data is not a dict, it is assumed to be a progress percentage."""
    if type(status) != str:
        raise ValueError('Invalid value for status; must be a string')
    if not data:
        raise ValueError('Data argument not found')

    result = {}
    if type(data) != dict:
        result['progress'] = data
    else:
        result = data
    result['status'] = status
    set_cache_raw(progress_key, result, DEFAULT_TIMEOUT)


def get_cache(progress_key):
    """Unpickles the cache key to a dictionary and resets the timeout"""
    data = django_cache.get(progress_key)
    set_cache(progress_key, data['status'], data)
    return data


def lock_cache(progress_key, timeout=60):
    """Set the lock with a default timeout of 1 minute"""
    set_cache_raw(progress_key, 1, timeout)


def unlock_cache(progress_key, timeout=DEFAULT_TIMEOUT):
    """Unset the lock"""
    set_cache_raw(progress_key, 0, timeout)


def get_lock(progress_key):
    return get_cache_raw(progress_key)


def increment_cache(key, increment):
    """Increment cache by value increment, never exceed 100."""
    value = get_cache(key) or {'status': 'parsing', 'progress': 0.0}
    value = float(value['progress'])
    if value + increment >= 100.0:
        value = 100.0
    else:
        value += increment

    set_cache(key, 'parsing', value)
