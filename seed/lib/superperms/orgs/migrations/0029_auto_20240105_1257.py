# Generated by Django 3.2.23 on 2024-01-05 20:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0028_organization_audit_template_report_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="display_units_ghg",
            field=models.CharField(
                choices=[("kgCO2e/year", "kgCO2e/year"), ("MtCO2e/year", "MtCO2e/year")], default="MtCO2e/year", max_length=32
            ),
        ),
        migrations.AlterField(
            model_name="organization",
            name="display_units_ghg_intensity",
            field=models.CharField(
                choices=[
                    ("kgCO2e/ft**2/year", "kgCO2e/ft²/year"),
                    ("MtCO2e/ft**2/year", "MtCO2e/ft²/year"),
                    ("kgCO2e/m**2/year", "kgCO2e/m²/year"),
                    ("MtCO2e/m**2/year", "MtCO2e/m²/year"),
                ],
                default="kgCO2e/ft**2/year",
                max_length=32,
            ),
        ),
    ]
