"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
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
        if self._completed % 10000 == 0:
            print(f"... {self._completed:,} / {self._total:,} ({self._updated:,} updated in {datetime.now() - self._start}) ...")


def rehash(apps, properties=True, taxlots=True):
    with transaction.atomic(), connection.cursor() as cursor:
        model = {}
        if properties:
            model["seed_propertystate"] = apps.get_model("seed", "PropertyState")
        if taxlots:
            model["seed_taxlotstate"] = apps.get_model("seed", "TaxLotState")

        for table in model:
            count = model[table].objects.count()
            if count > 0:
                print(f"\nRe-hashing {table} ({count:,} states)")
                cursor.execute(f"PREPARE update_hash (integer, text) AS UPDATE {table} SET hash_object = $2 WHERE id = $1;")  # noqa: S608
                progress = ProgressLogger(count)

                # Check if SEED migration 0225 has run yet
                excluded_migration_complete = MigrationRecorder.Migration.objects.filter(
                    app="seed", name="0225_column_is_excluded_from_hash"
                ).exists()

                # Pre-fetch the column names for every org with states
                org_ids: list[int] = list(model[table].objects.values_list("organization_id", flat=True).distinct())
                prefetched_columns: dict[int, list[str]] = {}
                for org_id in org_ids:
                    if excluded_migration_complete:
                        prefetched_columns[org_id] = Column.retrieve_db_field_name_for_hash_comparison(model[table], org_id)
                    else:
                        # Use the old rehash methodology for databases that need to run rehash migrations prior to the
                        # `is_excluded_from_hash` column being added in `0225_column_is_excluded_from_hash.py`
                        prefetched_columns[org_id] = sorted({c["column_name"] for c in Column.retrieve_db_fields_from_db_tables()})

                for idx, state in enumerate(model[table].objects.iterator(chunk_size=1000)):
                    old_hash = state.hash_object
                    new_hash = hash_state_object(state, prefetched_columns=prefetched_columns.get(state.organization_id))

                    update = new_hash != old_hash
                    if update:
                        cursor.execute("EXECUTE update_hash (%s, %s);", (state.id, new_hash))
                    progress.increment(update)

                print(f"  {progress.updated:,} {table} hash{'' if progress.updated == 1 else 'es'} updated")
                cursor.execute("DEALLOCATE update_hash;")
