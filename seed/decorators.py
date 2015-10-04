"""
:copyright: (c) 2014 Building Energy Inc
"""
from functools import wraps

from seed.utils.cache import make_key, lock_cache, unlock_cache, get_lock

SEED_CACHE_PREFIX = 'SEED:{0}'
LOCK_CACHE_PREFIX = SEED_CACHE_PREFIX + ':LOCK'
PROGRESS_CACHE_PREFIX = SEED_CACHE_PREFIX + ':PROG'


def _get_cache_key(prefix, import_file_pk):
    """Makes a key like 'SEED:save_raw_data:LOCK:45'."""
    return make_key(
        '{0}:{1}'.format(prefix, import_file_pk)
    )


def _get_lock_key(func_name, import_file_pk):
    return _get_cache_key(
        LOCK_CACHE_PREFIX.format(func_name), import_file_pk
    )


def get_prog_key(func_name, import_file_pk):
    """Return the progress key for the cache"""
    return _get_cache_key(
        PROGRESS_CACHE_PREFIX.format(func_name), import_file_pk
    )


def lock_and_track(fn, *args, **kwargs):
    """Decorator to lock tasks to single executor and provide progress url."""
    func_name = fn.__name__

    @wraps(fn)
    def _wrapped(import_file_pk, *args, **kwargs):
        """Lock and return progress url for updates."""
        lock_key = _get_lock_key(func_name, import_file_pk)
        prog_key = get_prog_key(func_name, import_file_pk)
        is_locked = get_lock(lock_key)
        # If we're already processing a given task, don't proceed.
        if is_locked:
            return {'error': 'locked'}

        # Otherwise, set the lock for 1 minute.
        lock_cache(lock_key)
        try:
            response = fn(import_file_pk, *args, **kwargs)
        finally:
            # Unset our lock
            unlock_cache(lock_key)

        # If our response is a dict, add our progress URL to it.
        if isinstance(response, dict):
            response['progress_key'] = prog_key

        return response

    return _wrapped
