"""
:copyright: (c) 2014 Building Energy Inc
"""
from functools import wraps

from django.core.cache import cache

SEED_CACHE_PREFIX = 'SEED:{0}'
LOCK_CACHE_PREFIX = SEED_CACHE_PREFIX + ':LOCK'
PROGRESS_CACHE_PREFIX = SEED_CACHE_PREFIX + ':PROG'


def _get_cache_key(prefix, import_file_pk):
    """Makes a key like 'SEED:save_raw_data:LOCK:45'."""
    return unicode(cache.make_key(
        '{0}:{1}'.format(prefix, import_file_pk)
    ))


def _get_lock_key(func_name, import_file_pk):
    return _get_cache_key(LOCK_CACHE_PREFIX.format(func_name), import_file_pk)


def get_prog_key(func_name, import_file_pk):
    """Return the progress key for the cache"""
    return _get_cache_key(
        PROGRESS_CACHE_PREFIX.format(func_name), import_file_pk
    )


def increment_cache(key, increment):
    """Increment cache by value increment, never exceed 100."""
    value = cache.get(key) or {'status': 'parsing', 'progress': 0.0}
    value = float(value['progress'])
    if value + increment >= 100.0:
        value = 100.0
    else:
        value += increment

    cache.set(key, {'status': 'parsing', 'progress': value})


def lock_and_track(fn, *args, **kwargs):
    """Decorator to lock tasks to single executor and provide progress url."""
    func_name = fn.__name__

    @wraps(fn)
    def _wrapped(import_file_pk, *args, **kwargs):
        """Lock and return progress url for updates."""
        lock_key = _get_lock_key(func_name, import_file_pk)
        prog_key = get_prog_key(func_name, import_file_pk)
        is_locked = cache.get(lock_key)
        # If we're already processing a given task, don't proceed.
        if is_locked:
            return {'error': 'locked'}

        # Otherwise, set the lock for 1 minute.
        cache.set(lock_key, 1, 60)
        try:
            response = fn(import_file_pk, *args, **kwargs)
        finally:
            # Unset our lock
            cache.set(lock_key, 0)

        # If our response is a dict, add our progress URL to it.
        if isinstance(response, dict):
            response['progress_key'] = prog_key

        return response

    return _wrapped
