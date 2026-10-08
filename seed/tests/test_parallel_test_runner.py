from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from seed.backends.postgis_timescaledb_tests.runner import ParallelTestRunner


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
