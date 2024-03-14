"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

Basic flipper library for hiding OGBS features for dark-launch

Could get super-complicated with this (e.g., see https://github.com/disqus/gutter)
but our needs are pretty simple:

  - easily greppable to remove them later
  - boolean-only gate is fine (no progressive roll-out, deploy groups needed yet)
  - redeploy to toggle is OK, ie. no real persistence beyond the filesystem

Most of the adds here are based on some experience in doing dark-launch, in
that a major hazard is that this counts as high-interest technical debt and
can get out of hand if we don't clean them up:

  - will get a unit test failure if the flipper is too old
  - will get a noisy log message if used past the expires date to discourage
    flippers from hanging around after they're needed.

no point in following any particular API since:
  - if we need something more complicated we'll use a better lib
  - flippers shouldn't stick around long so we don't want to encourage
    sticking around by future-proofing the API.
"""
import datetime

import pytz
from django.utils.dateparse import parse_datetime

REGISTRY = {}


def make_flipper(owner, expires, label, kind, initial_value):
    """
    Adds a flipper to the module's registry
    all values string, returns dict
    """
    flipper = {
        'label': label,
        kind: initial_value,
        'expires': expires,
        'owner': owner
    }
    REGISTRY[label] = flipper
    return flipper


def _is_stale(flipper, date):
    expires_str = flipper.get('expires', '')
    expires = parse_datetime(expires_str)
    if expires:
        return date > expires
    return False


def _log_stale_flipper(flipper):
    owner = flipper.get('owner', 'unknown owner')
    label = flipper.get('label', 'unknown label')
    print("Flipper '{}' is stale; tell {} to tidy up".format(label, owner))


def is_active(s, now=datetime.datetime.now(pytz.UTC)):
    """
    Checks if the flipper is active, use for hiding feature eg:
    ```
    if flipper.is_active('my_awesome_feature'):
        do_feature()
    ```
    """
    flipper = REGISTRY.get(s, {'boolean': False})
    if _is_stale(flipper, now):
        _log_stale_flipper(flipper)
    return flipper['boolean']
