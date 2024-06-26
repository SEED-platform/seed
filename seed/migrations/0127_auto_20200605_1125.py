# Generated by Django 2.2.10 on 2020-06-05 18:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0126_columnmappingpreset_preset_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="column",
            name="comstock_mapping",
            field=models.CharField(blank=True, default=None, max_length=64, null=True),
        ),
        migrations.AddConstraint(
            model_name="column",
            constraint=models.UniqueConstraint(fields=("organization", "comstock_mapping"), name="unique_comstock_mapping"),
        ),
    ]
