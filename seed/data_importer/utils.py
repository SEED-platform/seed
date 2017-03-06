# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
"""
Utility methods pertaining to data import tasks (save, mapping, matching).
"""
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone


def get_core_pk_column(table_column_mappings, primary_field):
    for tcm in table_column_mappings:
        if tcm.destination_field == primary_field:
            return tcm.order - 1
    raise ValidationError("This file doesn't appear to contain a column mapping to %s" % primary_field)


def acquire_lock(name, expiration=None):
    """
    Tries to acquire a lock from the cache.
    Also sets the lock's value to the current time, allowing us to see how long
    it has been held.

    Returns False if lock already belongs by another process.
    """
    return cache.add(name, timezone.now(), expiration)


def release_lock(name):
    """
    Frees a lock.
    """
    return cache.delete(name)


def get_lock_time(name):
    """
    Examines a lock to see when it was acquired.
    """
    return cache.get(name)


def chunk_iterable(iter, chunk_size):
    """
    Breaks an iterable (e.g. list) into smaller chunks,
    returning a generator of the chunk.
    """
    assert hasattr(iter, "__iter__"), "iter is not an iterable"
    for i in xrange(0, len(iter), chunk_size):
        yield iter[i:i + chunk_size]


class CoercionRobot(object):

    def __init__(self):
        self.values_hash = {}

    def lookup_hash(self, uncoerced_value, destination_model, destination_field):
        key = self.make_key(uncoerced_value, destination_model, destination_field)
        if key in self.values_hash:
            return self.values_hash[key]
        return None

    def make_key(self, value, model, field):
        return "%s|%s|%s" % (value, model, field)
