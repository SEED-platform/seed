"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import datetime

from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder

from seed.data_importer.tasks import hash_state_object
from seed.models import Column


class ProgressLogger:
    def __init__(self, total: int):
        self._start = datetime.now()
        self._completed = 0
        self._updated = 0
        self._total = total

    @property
    def updated(self):
        return self._updated

    def increment(self, update: bool):
        self._completed = self._completed + 1
        if update:
            self._updated = self._updated + 1
        if self._completed % 10_000 == 0:
            print(f"... {self._completed:,} / {self._total:,} ({self._updated:,} updated in {datetime.now() - self._start}) ...")


def rehash(apps, properties=True, taxlots=True):
    with transaction.atomic(), connection.cursor() as cursor:
        model = {}
        if properties:
            model["seed_propertystate"] = apps.get_model("seed", "PropertyState")
        if taxlots:
            model["seed_taxlotstate"] = apps.get_model("seed", "TaxLotState")

        for table, state_model in model.items():
            count = state_model.objects.count()
            if count > 0:
                print(f"\nRe-hashing {table} ({count:,} states)")
                cursor.execute(f"PREPARE update_hash (integer, text) AS UPDATE {table} SET hash_object = $2 WHERE id = $1;")  # noqa: S608
                progress = ProgressLogger(count)

                # Check if SEED migration 0225 has run yet
                excluded_migration_complete = MigrationRecorder.Migration.objects.filter(
                    app="seed", name="0225_column_is_excluded_from_hash"
                ).exists()

                # Pre-fetch the column names for every org with states
                org_ids: list[int] = list(state_model.objects.values_list("organization_id", flat=True).distinct())
                prefetched_columns: dict[int, list[str]] = {}
                for org_id in org_ids:
                    if excluded_migration_complete:
                        prefetched_columns[org_id] = Column.retrieve_db_field_name_for_hash_comparison(state_model, org_id)
                    else:
                        # Use the old rehash methodology for databases that need to run rehash migrations prior to the
                        # `is_excluded_from_hash` column being added in `0225_column_is_excluded_from_hash.py`
                        prefetched_columns[org_id] = sorted({c["column_name"] for c in Column.retrieve_db_fields_from_db_tables()})

                for idx, state in enumerate(state_model.objects.iterator(chunk_size=1_000)):
                    old_hash = state.hash_object
                    new_hash = hash_state_object(state, prefetched_columns=prefetched_columns.get(state.organization_id))

                    update = new_hash != old_hash
                    if update:
                        cursor.execute("EXECUTE update_hash (%s, %s);", (state.id, new_hash))
                    progress.increment(update)

                print(f"  {progress.updated:,} {table} hash{'' if progress.updated == 1 else 'es'} updated")
                cursor.execute("DEALLOCATE update_hash;")


# ---------------------------------------------------------------------------
# Primary key / constraint "repair" helpers.
#
# Some production databases were restored (or historically created) without the
# primary key / unique constraints that Django's migration history assumes
# already exist. When a later migration adds a foreign key that references one
# of those tables, PostgreSQL rejects it because the referenced column is not
# backed by a primary key or unique constraint -- even though Django believes
# the historical migrations already ran.
#
# The helpers below build guarded SQL so a repair is safe to run repeatedly and
# on healthy databases that already have the constraints. Every generated
# statement is wrapped in ``pg_catalog`` existence checks, so it is a no-op
# unless the constraint is genuinely missing.
# ---------------------------------------------------------------------------

_SAFE_IDENT_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


def _validate_identifier(name: str) -> str:
    """Guard the table/constraint names we interpolate into repair SQL.

    These values always come from migration source code (never user input), but
    validating keeps the generated SQL obviously safe and fails loudly on typos.
    """
    if not name or name[0].isdigit() or any(char not in _SAFE_IDENT_CHARS for char in name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name


def add_missing_primary_keys_sql(*tables: str) -> str:
    """Return idempotent SQL adding an ``id`` PRIMARY KEY to each named table.

    Each table is repaired only when it exists, has an ``id`` column, and does
    not already have a primary key. Use this when a migration needs a specific
    set of tables repaired before it can add foreign keys that reference them.
    """
    blocks = []
    for table in tables:
        _validate_identifier(table)
        blocks.append(
            f"""
    IF to_regclass('public.{table}') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
           WHERE conrelid = to_regclass('public.{table}') AND contype = 'p'
       )
       AND EXISTS (
           SELECT 1 FROM pg_attribute
           WHERE attrelid = to_regclass('public.{table}')
             AND attname = 'id' AND attnum > 0 AND NOT attisdropped
       ) THEN
        ALTER TABLE public.{table} ADD CONSTRAINT {table}_pkey PRIMARY KEY (id);
        RAISE NOTICE 'Repaired missing primary key on public.{table}';
    END IF;
"""  # noqa: S608
        )
    return "DO $$\nBEGIN" + "".join(blocks) + "END;\n$$;"


def add_missing_unique_constraint_sql(table: str, constraint: str, *columns: str) -> str:
    """Return idempotent SQL adding a named UNIQUE constraint when it is missing."""
    _validate_identifier(table)
    _validate_identifier(constraint)
    for column in columns:
        _validate_identifier(column)
    column_list = ", ".join(columns)
    return f"""DO $$
BEGIN
    IF to_regclass('public.{table}') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM pg_constraint
           WHERE conrelid = to_regclass('public.{table}') AND conname = '{constraint}'
       ) THEN
        ALTER TABLE public.{table} ADD CONSTRAINT {constraint} UNIQUE ({column_list});
        RAISE NOTICE 'Repaired missing unique constraint {constraint} on public.{table}';
    END IF;
END;
$$;"""  # noqa: S608


def repair_all_missing_primary_keys_sql(*table_prefixes: str) -> str:
    """Return idempotent SQL repairing every table missing its ``id`` primary key.

    Dynamically scans ``public`` for ordinary tables whose name starts with one
    of ``table_prefixes`` (e.g. ``"seed_"``, ``"orgs_"``) that have an ``id``
    column but no primary key, and adds ``<table>_pkey PRIMARY KEY (id)``. This
    guarantees completeness: no table is ever missed as new models are added.

    Tables with a natural / composite primary key (no ``id`` column) are skipped,
    which is what we want -- their primary key lives on a different column.
    """
    if not table_prefixes:
        raise ValueError("repair_all_missing_primary_keys_sql requires at least one prefix")
    prefix_conditions = " OR ".join(f"starts_with(c.relname, '{_validate_identifier(prefix)}')" for prefix in table_prefixes)
    return f"""DO $$
DECLARE
    rec record;
BEGIN
    FOR rec IN
        SELECT c.oid, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND ({prefix_conditions})
          AND NOT EXISTS (
              SELECT 1 FROM pg_constraint pc
              WHERE pc.conrelid = c.oid AND pc.contype = 'p'
          )
          AND EXISTS (
              SELECT 1 FROM pg_attribute a
              WHERE a.attrelid = c.oid
                AND a.attname = 'id' AND a.attnum > 0 AND NOT a.attisdropped
          )
    LOOP
        EXECUTE format(
            'ALTER TABLE public.%I ADD CONSTRAINT %I PRIMARY KEY (id)',
            rec.relname, rec.relname || '_pkey'
        );
        RAISE NOTICE 'Repaired missing primary key on public.%', rec.relname;
    END LOOP;
END;
$$;"""  # noqa: S608
