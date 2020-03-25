# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from django.db import connection, migrations


def forwards(apps, schema_editor):
    property_sql = (
        'UPDATE seed_propertystate '
        'SET updated = (SELECT created '
        '               FROM seed_propertyauditlog '
        '               WHERE seed_propertystate.id = state_id '
        '               ORDER BY created DESC '
        '               LIMIT 1) '
        'FROM seed_propertyauditlog '
        'WHERE seed_propertystate.id = state_id;'
    )

    taxlot_sql = (
        'UPDATE seed_taxlotstate '
        'SET updated = (SELECT created '
        '               FROM seed_taxlotauditlog '
        '               WHERE seed_taxlotstate.id = state_id '
        '               ORDER BY created DESC '
        '               LIMIT 1) '
        'FROM seed_taxlotauditlog '
        'WHERE seed_taxlotstate.id = state_id;'
    )

    with connection.cursor() as cursor:
        cursor.execute(property_sql)
        cursor.execute(taxlot_sql)


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0120_created_updated_col_objects'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
