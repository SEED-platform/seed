# Generated by Django 1.9.5 on 2017-03-07 17:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0050_clean_auditlogs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="propertyauditlog",
            name="parent_state1",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="propertyauditlog__parent_state1",
                to="seed.PropertyState",
            ),
        ),
        migrations.AlterField(
            model_name="propertyauditlog",
            name="parent_state2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="propertyauditlog__parent_state2",
                to="seed.PropertyState",
            ),
        ),
        migrations.AlterField(
            model_name="propertyauditlog",
            name="record_type",
            field=models.IntegerField(blank=True, choices=[(0, "ImportFile"), (1, "UserEdit")], null=True),
        ),
        migrations.AlterField(
            model_name="taxlotauditlog",
            name="parent_state1",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="taxlotauditlog__parent_state1",
                to="seed.TaxLotState",
            ),
        ),
        migrations.AlterField(
            model_name="taxlotauditlog",
            name="parent_state2",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="taxlotauditlog__parent_state2",
                to="seed.TaxLotState",
            ),
        ),
        migrations.AlterField(
            model_name="taxlotauditlog",
            name="record_type",
            field=models.IntegerField(blank=True, choices=[(0, "ImportFile"), (1, "UserEdit")], null=True),
        ),
    ]
