"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import unittest
from argparse import ArgumentTypeError
from unittest.mock import Mock, patch

import pytest
from django.test import SimpleTestCase

from seed.backends.postgis_timescaledb_tests.runner import ParallelTestRunner, parse_shard


def make_tests(module, class_name, count):
    test_class = type(class_name, (unittest.TestCase,), {f"test_{i}": lambda _: None for i in range(count)})
    test_class.__module__ = module
    return [test_class(f"test_{i}") for i in range(count)]


class TestParallelTestRunner(SimpleTestCase):
    @patch("seed.backends.postgis_timescaledb_tests.runner.connections")
    @patch("django.test.runner.DiscoverRunner.setup_databases", return_value="database configuration")
    def test_passes_effective_parallel_process_count_to_database_backend(self, mock_setup_databases, mock_connections):
        connection = Mock()
        mock_connections.__getitem__.return_value = connection
        runner = ParallelTestRunner(parallel=32)
        runner.parallel = 5  # Django reduces the requested count while building the suite.

        result = runner.setup_databases(aliases={"default": False}, serialized_aliases=set())

        connection.creation.set_parallel_processes.assert_called_once_with(5)
        mock_setup_databases.assert_called_once_with(aliases={"default": False}, serialized_aliases=set())
        self.assertEqual(result, "database configuration")


class TestParallelTestRunnerShards(SimpleTestCase):
    def setUp(self):
        self.big = make_tests("app.test_big", "BigTests", 5)
        self.small_a = make_tests("app.test_small", "SmallATests", 1)
        self.small_b = make_tests("app.test_small", "SmallBTests", 2)
        self.mid = make_tests("app.test_mid", "MidTests", 3)

    def load_shard(self, shard):
        runner = ParallelTestRunner(shard=shard, verbosity=0)
        suite = unittest.TestSuite([*self.big, *self.small_a, *self.small_b, *self.mid])
        with patch("django.test.runner.DiscoverRunner.load_tests_for_label", return_value=suite):
            return list(runner.load_tests_for_label(".", {}))

    def test_shards_split_whole_modules_by_test_count(self):
        # Largest module first onto the emptiest shard: test_big (5) -> 1, then test_mid (3) and test_small (3) -> 2
        self.assertEqual(self.load_shard((1, 2)), self.big)
        # Within a shard, the largest classes come first
        self.assertEqual(self.load_shard((2, 2)), [*self.mid, *self.small_b, *self.small_a])

    def test_shards_run_every_test_exactly_once(self):
        shards = [self.load_shard((index, 3)) for index in (1, 2, 3)]

        self.assertCountEqual([test for shard in shards for test in shard], [*self.big, *self.small_a, *self.small_b, *self.mid])

    def test_without_shard_returns_tests_unchanged(self):
        suite = unittest.TestSuite(self.big)
        with patch("django.test.runner.DiscoverRunner.load_tests_for_label", return_value=suite):
            self.assertIs(ParallelTestRunner(verbosity=0).load_tests_for_label(".", {}), suite)

    def test_parse_shard(self):
        self.assertEqual(parse_shard("2/6"), (2, 6))
        for value in ("0/6", "7/6", "6", "a/6", "-1/6"):
            with self.subTest(value=value), pytest.raises(ArgumentTypeError):
                parse_shard(value)
