# This rehashing file should be used in the future if needed as it has been optimized. Rehashing takes
# awhile and should be avoided if possible.

from django.db import connection, migrations

from seed.utils.migrations import rehash


def forwards(apps, schema_editor):
    property_sql = (
        "UPDATE seed_propertystate "
        "SET created = seed_propertyauditlog.created, updated = seed_propertyauditlog.created "
        "FROM seed_propertyauditlog "
        "WHERE seed_propertystate.id = state_id;"
    )

    taxlot_sql = (
        "UPDATE seed_taxlotstate "
        "SET created = seed_taxlotauditlog.created, updated = seed_taxlotauditlog.created "
        "FROM seed_taxlotauditlog "
        "WHERE seed_taxlotstate.id = state_id;"
    )

    with connection.cursor() as cursor:
        cursor.execute(property_sql)
        cursor.execute(taxlot_sql)


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0110_matching_criteria"),
    ]

    operations = [
        migrations.RunPython(lambda apps, _schema_editor: rehash(apps)),
        migrations.RunPython(forwards),
    ]
