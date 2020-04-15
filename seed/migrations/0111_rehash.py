# -*- coding: utf-8 -*-

# This rehashing file should be used in the future if needed as it has been optimized. Rehashing takes
# awhile and should be avoided if possible.
from __future__ import unicode_literals

# import time
# from datetime import timedelta

from django.db import connection, migrations, transaction

from seed.data_importer.tasks import hash_state_object


def forwards(apps, schema_editor):
    property_sql = (
        "UPDATE seed_propertystate " +
        "SET created = seed_propertyauditlog.created, updated = seed_propertyauditlog.created " +
        "FROM seed_propertyauditlog " +
        "WHERE seed_propertystate.id = state_id;"
    )

    taxlot_sql = (
        "UPDATE seed_taxlotstate " +
        "SET created = seed_taxlotauditlog.created, updated = seed_taxlotauditlog.created " +
        "FROM seed_taxlotauditlog " +
        "WHERE seed_taxlotstate.id = state_id;"
    )

    with connection.cursor() as cursor:
        cursor.execute(property_sql)
        cursor.execute(taxlot_sql)


# Go through every property and tax lot and simply save it to create the hash_object
def recalculate_hash_objects(apps, schema_editor):
    PropertyState = apps.get_model('seed', 'PropertyState')
    TaxLotState = apps.get_model('seed', 'TaxLotState')

    # find which columns are not used in column mappings
    property_count = PropertyState.objects.count()
    taxlot_count = TaxLotState.objects.count()
    # print("There are %s objects to traverse" % (property_count + taxlot_count))

    # start = time.clock()
    # print("Iterating over PropertyStates. Count %s" % property_count)
    with transaction.atomic():
        for idx, obj in enumerate(PropertyState.objects.all().iterator()):
            if idx % 1000 == 0:
                print("... %s / %s ..." % (idx, property_count))
            obj.hash_object = hash_state_object(obj)
            obj.save()

    # print("Iterating over TaxLotStates. Count %s" % taxlot_count)
    with transaction.atomic():
        for idx, obj in enumerate(TaxLotState.objects.all().iterator()):
            if idx % 1000 == 0:
                print("... %s / %s ..." % (idx, taxlot_count))
            obj.hash_object = hash_state_object(obj)
            obj.save()
    # execution_time = time.clock() - start
    # print(timedelta(seconds=execution_time))


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0110_matching_criteria'),
    ]

    operations = [
        migrations.RunPython(recalculate_hash_objects),
        migrations.RunPython(forwards),
    ]
