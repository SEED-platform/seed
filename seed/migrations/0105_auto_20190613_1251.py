# Generated by Django 1.11.21 on 2019-06-13 19:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0104_auto_20190509_1854"),
    ]

    operations = [
        migrations.AlterField(
            model_name="meter",
            name="type",
            field=models.IntegerField(
                choices=[
                    (1, "Coal (anthracite)"),
                    (2, "Coal (bituminous)"),
                    (3, "Coke"),
                    (4, "Diesel"),
                    (5, "District Chilled Water - Absorption"),
                    (6, "District Chilled Water - Electric"),
                    (7, "District Chilled Water - Engine"),
                    (8, "District Chilled Water - Other"),
                    (9, "District Hot Water"),
                    (10, "District Steam"),
                    (11, "Electric - Grid"),
                    (12, "Electric - Solar"),
                    (13, "Electric - Wind"),
                    (14, "Fuel Oil (No. 1)"),
                    (15, "Fuel Oil (No. 2)"),
                    (16, "Fuel Oil (No. 4)"),
                    (13, "Fuel Oil (No. 5 and No. 6)"),
                    (18, "Kerosene"),
                    (19, "Natural Gas"),
                    (20, "Other:"),
                    (21, "Propane"),
                    (22, "Wood"),
                    (23, "Cost"),
                ],
                default=None,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="meterreading",
            name="reading",
            field=models.FloatField(null=True),
        ),
    ]
