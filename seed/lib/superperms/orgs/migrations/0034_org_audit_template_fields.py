# Generated by Django 3.2.23 on 2024-03-13 15:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0033_organization_public_geojson_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="audit_template_city_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="audit_template_status_type",
            field=models.CharField(
                blank=True,
                choices=[("Complies", "Complies"), ("Pending", "Pending"), ("Rejected", "Rejected"), ("Received", "Complies")],
                default="Complies",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="audit_template_sync_enabled",
            field=models.BooleanField(default=False),
        ),
    ]