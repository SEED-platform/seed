# Generated by Django 1.9.5 on 2016-08-23 04:09

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0025_auto_20160822_2108"),
    ]

    operations = [
        migrations.RenameField(
            model_name="taxlotauditlog",
            old_name="child",
            new_name="state",
        ),
    ]
