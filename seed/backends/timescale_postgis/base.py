"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

TimescaleDB + PostGIS database backend for SEED.

This wraps ``timescale.db.backends.postgis`` and swaps in a schema editor that
fixes an upstream bug in the released ``django-timescaledb`` (0.2.13): its
PostGIS ``schema.py`` references ``settings`` inside ``_create_hypertable``
without importing it. That method is executed whenever an existing table is
migrated into a hypertable (our ``SensorReading.timestamp`` AlterField), so the
released package raises ``NameError: name 'settings' is not defined`` and the
migration fails. The fix exists on the project's ``master`` branch but has not
been released.

The base backend is still configurable through ``TIMESCALE_DB_BACKEND_BASE``
(defaults to PostGIS), so this composes with the parallel test backend used by
the test settings.

This workaround can be removed once a ``django-timescaledb`` release that
includes the upstream fix is available.
"""

from django.conf import settings
from timescale.db.backends.postgis.base import DatabaseWrapper as TimescaleDatabaseWrapper
from timescale.db.backends.postgis.schema import TimescaleSchemaEditor


class SeedTimescaleSchemaEditor(TimescaleSchemaEditor):
    def _create_hypertable(self, model, field, should_migrate=False):
        # Reimplemented from TimescaleSchemaEditor to reference ``settings`` from
        # this module's namespace, which the released package fails to import.
        self._assert_is_not_hypertable(model)
        self._drop_primary_key(model)

        partition_column = self.quote_value(field.column)
        interval = self.quote_value(field.interval)
        table = self.quote_value(model._meta.db_table)
        migrate = "true" if should_migrate else "false"

        if should_migrate and getattr(settings, "TIMESCALE_MIGRATE_HYPERTABLE_WITH_FRESH_TABLE", False):
            raise NotImplementedError()

        sql = self.sql_add_hypertable.format(table=table, partition_column=partition_column, interval=interval, migrate=migrate)
        self.execute(sql)


class DatabaseWrapper(TimescaleDatabaseWrapper):
    SchemaEditorClass = SeedTimescaleSchemaEditor
