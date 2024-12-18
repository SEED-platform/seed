# Generated by Django 3.2.25 on 2024-10-08 22:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0236_auto_20241004_1413"),
    ]

    operations = [
        migrations.AddField(
            model_name="meter",
            name="connection_type",
            field=models.IntegerField(
                choices=[
                    (1, "From Outside"),
                    (2, "To Outside"),
                    (3, "From Service To Patron"),
                    (4, "From Patron To Service"),
                    (5, "Total From Patron"),
                    (6, "Total To Patron"),
                ],
                default=1,
            ),
        ),
        migrations.AddField(
            model_name="meter",
            name="service",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="meters", to="seed.service"
            ),
        ),
    ]
