# Generated by Django 3.2.25 on 2024-03-20 19:40

import django.contrib.postgres.indexes
import django.core.validators
import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0031_encrypt_existing_audit_template_passwords"),
        ("seed", "0217_goal_commitment_sqft"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="uniformat",
            options={"ordering": ["code"]},
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="category",
            field=models.CharField(
                help_text="Represents the broad classification of the building element, indicating its general type or function within the construction process",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="code",
            field=models.CharField(help_text="The code representing the current Uniformat category", max_length=7, unique=True),
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="definition",
            field=models.CharField(
                help_text="A detailed explanation of the category, outlining its components, functions, and scope",
                max_length=1024,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="imperial_units",
            field=models.CharField(
                help_text="Specifies the unit of measurement used for quantifying the item in the Imperial system", max_length=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="metric_units",
            field=models.CharField(
                help_text="Specifies the unit of measurement used for quantifying the item in the Metric system", max_length=10, null=True
            ),
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="parent",
            field=models.ForeignKey(
                help_text="The higher-level Uniformat category that the current category is a child of",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="seed.uniformat",
            ),
        ),
        migrations.AlterField(
            model_name="uniformat",
            name="quantity_definition",
            field=models.CharField(
                help_text="Defines how the quantity of the item is measured and expressed, providing context for interpreting the units",
                max_length=100,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="Element",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created")),
                ("modified", django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified")),
                ("element_id", models.CharField(db_index=True, max_length=36, null=True)),
                ("description", models.TextField(db_collation="natural_sort", null=True)),
                ("installation_date", models.DateField(db_index=True, null=True)),
                (
                    "condition_index",
                    models.FloatField(
                        null=True,
                        validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(100.0)],
                    ),
                ),
                ("remaining_service_life", models.FloatField(null=True)),
                ("replacement_cost", models.FloatField(null=True, validators=[django.core.validators.MinValueValidator(0.0)])),
                ("manufacturing_date", models.DateField(null=True)),
                ("extra_data", models.JSONField(default=dict)),
                ("code", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="elements", to="seed.uniformat")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="orgs.organization")),
                ("property", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="elements", to="seed.property")),
            ],
            options={
                "ordering": ["-installation_date", "description"],
            },
        ),
        migrations.AddIndex(
            model_name="element",
            index=django.contrib.postgres.indexes.GinIndex(fields=["extra_data"], name="extra_data_gin_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="element",
            unique_together={("organization", "element_id")},
        ),
    ]