# Generated by Django 1.9.5 on 2016-10-15 13:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0041_auto_20161014_1908"),
    ]

    operations = [
        migrations.AlterField(
            model_name="taxlotauditlog",
            name="state",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name="taxlotauditlog__state", to="seed.TaxLotState"
            ),
        ),
    ]
