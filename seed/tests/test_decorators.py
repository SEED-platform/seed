# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.test import TestCase

from seed import decorators
from seed.utils.cache import make_key, get_cache, get_lock, increment_cache, clear_cache

class TestException(Exception):
    pass


class TestDecorators(TestCase):
    """Tests for locking tasks and reporting progress."""

    locked = 1
    unlocked = 0
    pk = 34  # Arbitrary PK value to test with.

    def setUp(self):
        clear_cache()

    ## Tests for decorators utility functions

    def test_get_prog_key(self):
        """We format our cache key properly."""
        expected = make_key('SEED:fun_func:PROG:' + str(self.pk))
        self.assertEqual(decorators.get_prog_key('fun_func', self.pk), expected)

    def test_increment_cache(self):
        """Sum our progress by increments properly."""
        expected = 25.0
        test_key = make_key('increment_test')
        increment = 25.0
        # Fresh increment, this initializes the value.
        increment_cache(test_key, increment)
        self.assertEqual(float(get_cache(test_key)['progress']), expected)

        # Increment an existing key
        increment_cache(test_key, increment)
        expected = 50.0
        self.assertEqual(float(get_cache(test_key)['progress']), expected)

        # This should put us well over 100.0 in incrementation w/o bounds check.
        for i in range(10):
            increment_cache(test_key, increment)

        expected = 100.0
        self.assertEqual(float(get_cache(test_key)['progress']), expected)

    ## Tests for decorators themselves.

    def test_locking(self):
        """Make sure we indicate we're locked iff we're inside the function."""
        key = decorators._get_lock_key('fake_func', self.pk)
        self.assertEqual(int(get_lock(key)), self.unlocked)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            self.assertEqual(int(get_lock(key)), self.locked)

        fake_func(self.pk)

        self.assertEqual(int(get_lock(key)), self.unlocked)

    def test_locking_w_exception(self):
        """Make sure we release our lock if we've had an exception."""
        key = decorators._get_lock_key('fake_func', self.pk)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            self.assertEqual(int(get_lock(key)), self.locked)
            raise TestException('Test exception!')

        self.assertRaises(TestException, fake_func, self.pk)
        # Even though execution failed part way through a call, we unlock.
        self.assertEqual(int(get_lock(key)), self.unlocked)

    def test_progress(self):
        """When a task finishes, it increments the progress counter properly."""
        increment = expected = 25.0
        key = decorators.get_prog_key('fake_func', self.pk)
        self.assertEqual(float(get_cache(key, 0.0)['progress']), 0.0)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            increment_cache(key, increment)

        fake_func(self.pk)

        self.assertEqual(float(get_cache(key, 0.0)['progress']), expected)

