# Generated by Django 3.2.19 on 2023-05-11 18:10

from django.db import migrations


def rename_ulid_column(apps, schema_editor):
    Column = apps.get_model("seed", "Column")

    Column.objects.filter(
        column_name="ulid",
        table_name="TaxLotState",
        is_extra_data=False,
    ).update(
        column_name="ubid",
        display_name="UBID",
        column_description="UBID",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0198_auto_20230703_0828"),
    ]

    operations = [
        migrations.RenameField(
            model_name="taxlotstate",
            old_name="ulid",
            new_name="ubid",
        ),
        migrations.RunPython(rename_ulid_column),
    ]
