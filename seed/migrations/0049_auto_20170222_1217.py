# Generated by Django 1.9.5 on 2017-02-22 20:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0048_auto_20170219_1214"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertyauditlog",
            name="parent_state1",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="propertyauditlog__parent_state1",
                to="seed.PropertyState",
            ),
        ),
        migrations.AddField(
            model_name="propertyauditlog",
            name="parent_state2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="propertyauditlog__parent_state2",
                to="seed.PropertyState",
            ),
        ),
        migrations.AddField(
            model_name="taxlotauditlog",
            name="parent_state1",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="taxlotauditlog__parent_state1",
                to="seed.TaxLotState",
            ),
        ),
        migrations.AddField(
            model_name="taxlotauditlog",
            name="parent_state2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="taxlotauditlog__parent_state2",
                to="seed.TaxLotState",
            ),
        ),
    ]
