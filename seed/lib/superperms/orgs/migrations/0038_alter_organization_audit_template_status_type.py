# Generated by Django 3.2.25 on 2024-08-19 12:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0037_organization_display_water_units"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="audit_template_status_type",
            field=models.CharField(blank=True, default="Complies", max_length=34),
        ),
        migrations.RenameField(
            model_name="organization",
            old_name="audit_template_status_type",
            new_name="audit_template_status_types",
        ),
    ]
