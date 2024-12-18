# Generated by Django 3.2.25 on 2024-10-22 15:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0039_alter_organization_ubid_threshold"),
        ("seed", "0231_column_is_updating"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportConfiguration",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                (
                    "access_level_instance",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="report_configurations",
                        to="orgs.accesslevelinstance",
                    ),
                ),
                ("access_level_depth", models.IntegerField(null=True)),
                ("cycles", models.ManyToManyField(related_name="report_configurations", to="seed.Cycle")),
                (
                    "filter_group",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.CASCADE, related_name="report_configurations", to="seed.filtergroup"
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="report_configurations", to="orgs.organization"
                    ),
                ),
                ("x_column", models.CharField(max_length=255, null=True)),
                ("y_column", models.CharField(max_length=255, null=True)),
            ],
        ),
    ]
