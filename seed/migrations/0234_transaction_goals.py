# Generated by Django 3.2.25 on 2024-12-02 22:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0233_alter_goal_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="goal",
            name="transactions_column",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="goal_transactions_columns",
                to="seed.column",
            ),
        ),
        migrations.AddField(
            model_name="goal",
            name="type",
            field=models.CharField(choices=[("standard", "standard"), ("transaction", "transaction")], default="standard", max_length=255),
        ),
    ]