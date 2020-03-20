# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def forwards(apps, schema_editor):
    Column = apps.get_model("seed", "Column")

    Column.objects.filter(
        column_name__in=['created', 'updated'],
        table_name='TaxLot',
        is_extra_data=False
    ).update(table_name='TaxLotState')

    Column.objects.filter(
        column_name__in=['created', 'updated'],
        table_name='Property',
        is_extra_data=False
    ).update(table_name='PropertyState')


def backwards(apps, schema_editor):
    Column = apps.get_model("seed", "Column")

    Column.objects.filter(
        column_name__in=['created', 'updated'],
        table_name='TaxLotState',
        is_extra_data=False
    ).update(table_name='TaxLot')

    Column.objects.filter(
        column_name__in=['created', 'updated'],
        table_name='PropertyState',
        is_extra_data=False
    ).update(table_name='Property')


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0119_column_recognize_empty'),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=backwards),
    ]
