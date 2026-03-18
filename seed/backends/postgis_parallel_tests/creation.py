from contextlib import contextmanager

from django.db.backends.postgresql.creation import DatabaseCreation as PostGISDatabaseCreation


class DatabaseCreation(PostGISDatabaseCreation):
    @contextmanager
    def _source_database_cursor(self):
        self.connection.close()
        try:
            with self.connection.cursor() as cursor:
                yield cursor
        finally:
            self.connection.close()

    def _enter_timescaledb_restore_mode(self):
        with self._source_database_cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
            if cursor.fetchone() is None:
                return False

            cursor.execute("SHOW timescaledb.restoring")
            if cursor.fetchone()[0].lower() == "on":
                return False

            # Timescale background workers attach to the template database and
            # block CREATE DATABASE ... WITH TEMPLATE during parallel test setup.
            cursor.execute("SELECT timescaledb_pre_restore()")
            return True

    def _exit_timescaledb_restore_mode(self):
        with self._source_database_cursor() as cursor:
            cursor.execute("SHOW timescaledb.restoring")
            if cursor.fetchone()[0].lower() == "on":
                cursor.execute("SELECT timescaledb_post_restore()")

    def _clone_test_db(self, suffix, verbosity, keepdb=False):
        restore_mode_changed = self._enter_timescaledb_restore_mode()
        try:
            super()._clone_test_db(suffix, verbosity, keepdb)
        finally:
            if restore_mode_changed:
                self._exit_timescaledb_restore_mode()
