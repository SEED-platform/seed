"""
:copyright: (c) 2014 Building Energy Inc
"""
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.test import TestCase


from seed import decorators


class TestException(Exception):
    pass

class TestDecorators(TestCase):
    """Tests for locking tasks and reporting progress."""

    locked = 1
    unlocked = 0
    pk = 34 # Arbitrary PK value to test with.

    def setUp(self):
        cache.clear()

    #
    ## Tests for decorators utility functions
    ### 

    def test_get_prog_key(self):
        """We format our cache key properly."""
        expected = cache.make_key('SEED:fun_func:PROG:34')
        self.assertEqual(decorators.get_prog_key('fun_func', 34), expected)

    def test_increment_cache(self):
        """Sum our progress by increments properly."""
        expected = 25.0
        test_key = cache.make_key('increment_test')
        increment = 25.0
        # Fresh increment, this initializes the value.
        decorators.increment_cache(test_key, increment)
        self.assertEqual(float(cache.get(test_key)['progress']), expected)

        # Increment an existing key
        decorators.increment_cache(test_key, increment)
        expected = 50.0
        self.assertEqual(float(cache.get(test_key)['progress']), expected)

        # This should put us well over 100.0 in incrementation w/o bounds check.
        for i in range(10):
            decorators.increment_cache(test_key, increment)

        expected = 100.0
        self.assertEqual(float(cache.get(test_key)['progress']), expected)

    #
    ## Tests for decorators themselves.
    ###

    def test_locking(self):
        """Make sure we indicate we're locked iff we're inside the function."""
        key = decorators._get_lock_key('fake_func', self.pk)
        self.assertEqual(int(cache.get(key, 0)), self.unlocked)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            self.assertEqual(int(cache.get(key, 0)), self.locked)

        fake_func(self.pk)

        self.assertEqual(int(cache.get(key, 0)), self.unlocked)

    def test_locking_w_exception(self):
        """Make sure we release our lock if we've had an exception."""
        key = decorators._get_lock_key('fake_func', self.pk)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            self.assertEqual(int(cache.get(key, 0)), self.locked)
            raise TestException('Test exception!')

        self.assertRaises(TestException, fake_func, self.pk)
        # Even though execution failed part way through a call, we unlock.
        self.assertEqual(int(cache.get(key, 0)), self.unlocked)

    def test_progress(self):
        """When a task finishes, it increments the progress counter properly."""
        increment = expected = 25.0
        key = decorators.get_prog_key('fake_func', self.pk)
        self.assertEqual(float(cache.get(key, 0.0)), 0.0)

        @decorators.lock_and_track
        def fake_func(import_file_pk):
            decorators.increment_cache(key, increment)

        fake_func(self.pk)

        self.assertEqual(float(cache.get(key, 0.0)['progress']), expected)
