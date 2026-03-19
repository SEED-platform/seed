import sys
from contextlib import contextmanager
from multiprocessing import cpu_count
from time import sleep

from django.db.backends.postgresql.creation import DatabaseCreation as PostGISDatabaseCreation


class DatabaseCreation(PostGISDatabaseCreation):
    _hold_restore_mode_for_parallel = False
    _block_source_database_connections = False
    _remaining_parallel_clones = 0

    @contextmanager
    def _source_database_cursor(self):
        self.connection.close()
        try:
            with self.connection.cursor() as cursor:
                yield cursor
        finally:
            self.connection.close()

    def _parallel_test_processes_requested(self):
        args = sys.argv[1:]
        for index, arg in enumerate(args):
            if arg == "--parallel":
                if index + 1 >= len(args) or args[index + 1].startswith("-"):
                    return cpu_count()
                value = args[index + 1]
            elif arg.startswith("--parallel="):
                value = arg.split("=", 1)[1]
            else:
                continue

            if value == "auto":
                return cpu_count()
            try:
                return int(value)
            except ValueError:
                return 0
        return 0

    def _source_database_name(self):
        return self.connection.settings_dict["NAME"]

    def _timescaledb_extension_installed(self):
        with self._source_database_cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
            return cursor.fetchone() is not None

    def _timescaledb_restore_mode_enabled(self):
        with self._source_database_cursor() as cursor:
            cursor.execute("SHOW timescaledb.restoring")
            return cursor.fetchone()[0].lower() == "on"

    def _enter_timescaledb_restore_mode(self):
        if not self._timescaledb_extension_installed():
            return False
        if self._timescaledb_restore_mode_enabled():
            return False

        with self._source_database_cursor() as cursor:
            # Timescale background workers attach to the template database and
            # block CREATE DATABASE ... WITH TEMPLATE during parallel test setup.
            cursor.execute("SELECT timescaledb_pre_restore()")
        return True

    def _exit_timescaledb_restore_mode(self):
        if not self._timescaledb_extension_installed():
            return
        if not self._timescaledb_restore_mode_enabled():
            return

        with self._source_database_cursor() as cursor:
            cursor.execute("SELECT timescaledb_post_restore()")

    def _set_source_database_allow_connections(self, allow_connections):
        source_database_name = self._source_database_name()
        quoted_source_database_name = self._quote_name(source_database_name)
        allow_connections_sql = "true" if allow_connections else "false"

        with self._nodb_cursor() as cursor:
            cursor.execute(f"ALTER DATABASE {quoted_source_database_name} WITH ALLOW_CONNECTIONS {allow_connections_sql}")

    def _disconnect_source_database_sessions(self):
        source_database_name = self._source_database_name()
        with self._nodb_cursor() as cursor:
            for _ in range(20):
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid()
                    """,
                    [source_database_name],
                )
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid()
                    """,
                    [source_database_name],
                )
                if cursor.fetchone()[0] == 0:
                    return
                sleep(0.25)

    def _finalize_parallel_clone_window(self):
        if self._block_source_database_connections:
            self._set_source_database_allow_connections(True)
            self._block_source_database_connections = False

        if self._hold_restore_mode_for_parallel and self._timescaledb_extension_installed():
            self._exit_timescaledb_restore_mode()
            self._hold_restore_mode_for_parallel = False

        self._remaining_parallel_clones = 0

    def create_test_db(self, verbosity=1, autoclobber=False, serialize=True, keepdb=False):
        test_database_name = super().create_test_db(
            verbosity=verbosity,
            autoclobber=autoclobber,
            serialize=serialize,
            keepdb=keepdb,
        )

        parallel_processes = self._parallel_test_processes_requested()
        if parallel_processes > 1:
            self._hold_restore_mode_for_parallel = self._enter_timescaledb_restore_mode() or self._timescaledb_restore_mode_enabled()
            self._set_source_database_allow_connections(False)
            self._block_source_database_connections = True
            self._disconnect_source_database_sessions()
            self._remaining_parallel_clones = parallel_processes

        return test_database_name

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        clone_succeeded = False
        try:
            if not self._hold_restore_mode_for_parallel:
                self._enter_timescaledb_restore_mode()
            self._disconnect_source_database_sessions()
            super()._clone_test_db(suffix, verbosity, keepdb)
            clone_succeeded = True
        finally:
            if self._hold_restore_mode_for_parallel:
                if clone_succeeded and self._remaining_parallel_clones > 0:
                    self._remaining_parallel_clones -= 1
                else:
                    self._remaining_parallel_clones = 0

                if self._remaining_parallel_clones == 0:
                    self._finalize_parallel_clone_window()

    def destroy_test_db(self, old_database_name=None, verbosity=1, keepdb=False, suffix=None):
        if suffix is None:
            self._finalize_parallel_clone_window()
        super().destroy_test_db(old_database_name, verbosity, keepdb, suffix)
