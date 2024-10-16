# Generated by Django 1.11.6 on 2018-08-17 18:12

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0006_organization_display_significant_figures"),
        ("data_importer", "0011_auto_20180725_0825"),
        ("seed", "0092_add_hash_object_data"),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="propertystate",
            index_together={
                ("import_file", "data_state"),
                ("import_file", "data_state", "source_type"),
                ("hash_object",),
                ("analysis_state", "organization"),
                ("import_file", "data_state", "merge_state"),
            },
        ),
    ]
