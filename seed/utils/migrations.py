"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import datetime

from django.db import connection, transaction

from seed.data_importer.tasks import hash_state_object


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
                print(f"Re-hashing {table} ({count:,} states)")
                cursor.execute(f"PREPARE update_hash (integer, text) AS UPDATE {table} SET hash_object = $2 WHERE id = $1;")  # noqa: S608
                progress = ProgressLogger(count)
                for idx, state in enumerate(model[table].objects.iterator(chunk_size=1000)):
                    old_hash = state.hash_object
                    new_hash = hash_state_object(state)

                    update = new_hash != old_hash
                    if update:
                        cursor.execute("EXECUTE update_hash (%s, %s);", (state.id, new_hash))
                    progress.increment(update)

                print(f"  {progress.updated:,} {table} hash{'' if progress.updated == 1 else 'es'} updated")
                cursor.execute("DEALLOCATE update_hash;")
