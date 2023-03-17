"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import cProfile
import pstats

from django.utils.functional import wraps


def cprofile(sort_by='cumulative', n=20):
    """Decorator to profile a function."""

    def decorator(func):
        @wraps(func)
        def profiled_func(*args, **kwargs):
            profile = cProfile.Profile()
            try:
                profile.enable()
                result = func(*args, **kwargs)
                profile.disable()
                return result
            finally:
                _print_profile(profile, sort_by=sort_by, n=n)

        return profiled_func

    return decorator


def _print_profile(profile, sort_by='cumulative', n=20):
    """Print top profiling results to console."""
    pstats.Stats(profile).sort_stats(sort_by).print_stats(n)


def _dump_profile(profile, filename, sort_by='time'):
    """Dump full profiling to file."""
    f = open(filename, 'a')
    pstats.Stats(profile, stream=f).sort_stats(sort_by).print_stats()
    f.close()
