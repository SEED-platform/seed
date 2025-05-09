# Generated by Django 1.11.6 on 2018-01-19 18:21

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orgs", "0004_auto_20180106_2123"),
        ("seed", "0081_merge_20180109_0747"),
    ]

    operations = [
        migrations.CreateModel(
            name="Note",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, verbose_name="name")),
                ("note_type", models.IntegerField(choices=[(0, b"Note"), (1, b"Log")], default=0, null=True)),
                ("text", models.TextField()),
                ("log_data", models.JSONField(default=dict, null=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="orgs.Organization"),
                ),
                (
                    "property_view",
                    models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="seed.PropertyView"),
                ),
                (
                    "taxlot_view",
                    models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notes", to="seed.TaxLotView"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notes", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "ordering": ["-created"],
            },
        ),
        migrations.AlterIndexTogether(
            name="note",
            index_together={("organization", "note_type")},
        ),
    ]
