# Generated by Django 1.11.6 on 2018-04-23 16:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0087_merge_20180123_1033"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertystate",
            name="latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="propertystate",
            name="longitude",
            field=models.FloatField(blank=True, null=True),
        ),
    ]
