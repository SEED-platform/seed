# Generated by Django 3.2.25 on 2024-11-06 21:39

import quantityfield.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0239_auto_20241030_1434"),
    ]

    operations = [
        migrations.AlterField(
            model_name="batterysystem",
            name="efficiency",
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name="meter",
            name="connection_type",
            field=models.IntegerField(
                choices=[
                    (1, "Imported"),
                    (2, "Exported"),
                    (3, "Receiving Service"),
                    (4, "Returning To Service"),
                    (5, "Total From Users"),
                    (6, "Total To Users"),
                ],
                default=1,
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="emission_factor",
            field=models.FloatField(null=True),
        ),
        migrations.RemoveField(
            model_name="batterysystem",
            name="capacity",
        ),
        migrations.RemoveField(
            model_name="dessystem",
            name="capacity",
        ),
        migrations.AddField(
            model_name="batterysystem",
            name="energy_capacity",
            field=quantityfield.fields.QuantityField(base_units="kWh", default=1, unit_choices=["kWh"]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="batterysystem",
            name="power_capacity",
            field=quantityfield.fields.QuantityField(base_units="kW", default=1, unit_choices=["kW"]),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="dessystem",
            name="cooling_capacity",
            field=quantityfield.fields.QuantityField(base_units="Ton", null=True, unit_choices=["Ton"]),
        ),
        migrations.AddField(
            model_name="dessystem",
            name="heating_capacity",
            field=quantityfield.fields.QuantityField(base_units="MMBtu", null=True, unit_choices=["MMBtu"]),
        ),
        migrations.AddField(
            model_name="evsesystem",
            name="voltage",
            field=quantityfield.fields.QuantityField(base_units="V", default=1, unit_choices=["V"]),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="batterysystem",
            name="voltage",
            field=quantityfield.fields.QuantityField(base_units="V", unit_choices=["V"]),
        ),
        migrations.AlterField(
            model_name="evsesystem",
            name="power",
            field=quantityfield.fields.QuantityField(base_units="kW", unit_choices=["kW"]),
        ),
        migrations.AddConstraint(
            model_name="dessystem",
            constraint=models.CheckConstraint(
                check=models.Q(("heating_capacity__isnull", False), ("cooling_capacity__isnull", False), _connector="OR"),
                name="heating_or_cooling_capacity_required",
            ),
        ),
    ]