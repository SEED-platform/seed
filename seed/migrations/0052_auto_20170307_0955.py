# Generated by Django 1.9.5 on 2017-03-07 17:55

from django.db import migrations


def forwards(apps, schema_editor):
    Column = apps.get_model("seed", "Column")

    columns = Column.objects.filter(extra_data_source__in=["P", "T"], table_name="")
    for c in columns:
        if c.extra_data_source == "P":
            c.table_name = "PropertyState"
        elif c.extra_data_source == "T":
            c.table_name = "TaxLotState"

        c.save()


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0051_auto_20170307_0954"),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
