# Generated by Django 3.2.13 on 2022-06-22 21:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0020_rename_display_significant_figures_organization_display_decimal_places"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="at_api_token",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="organization",
            name="at_organization_token",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
    ]
