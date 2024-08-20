"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from seed.data_importer.tasks import hash_state_object
from seed.models import PropertyState, TaxLotState


class Command(BaseCommand):
    help = "Rehashes all Property and TaxLot states, and reports how many were modified"

    def handle(self, *args, **options):
        with transaction.atomic(), connection.cursor() as cursor:
            property_count = PropertyState.objects.count()
            taxlot_count = TaxLotState.objects.count()

            properties_updated = 0
            taxlots_updated = 0

            if property_count > 0:
                print(f"Re-hashing {property_count:,} Property State{'' if property_count == 1 else 's'}")
                cursor.execute("PREPARE update_hash (integer, text) AS " "UPDATE seed_propertystate SET hash_object = $2 WHERE id = $1;")
                start = datetime.now()
                for idx, state in enumerate(PropertyState.objects.iterator(chunk_size=1000)):
                    old_hash = state.hash_object
                    new_hash = hash_state_object(state)

                    if new_hash != old_hash:
                        cursor.execute("EXECUTE update_hash (%s, %s);", (state.id, new_hash))
                        properties_updated += 1
                    if (idx + 1) % 10000 == 0:
                        print(f"... {idx + 1:,} / {property_count:,} ({properties_updated:,} updated in {datetime.now() - start}) ...")

                print(f"  {properties_updated:,} Property State hash{'' if property_count == 1 else 'es'} updated")
                cursor.execute("DEALLOCATE update_hash;")

            if taxlot_count > 0:
                print(f"Re-hashing {taxlot_count:,} TaxLot State{'' if taxlot_count == 1 else 's'}")
                cursor.execute("PREPARE update_hash (integer, text) AS " "UPDATE seed_taxlotstate SET hash_object = $2 WHERE id = $1;")
                start = datetime.now()
                for idx, state in enumerate(TaxLotState.objects.iterator(chunk_size=1000)):
                    old_hash = state.hash_object
                    new_hash = hash_state_object(state)

                    if new_hash != old_hash:
                        cursor.execute("EXECUTE update_hash (%s, %s);", (state.id, new_hash))
                        taxlots_updated += 1
                    if (idx + 1) % 10000 == 0:
                        print(f"... {idx + 1:,} / {taxlot_count:,} ({taxlots_updated:,} updated in {datetime.now() - start}) ...")

                print(f"  {taxlots_updated:,} TaxLot State hash{'' if taxlot_count == 1 else 'es'} updated")
                cursor.execute("DEALLOCATE update_hash;")
