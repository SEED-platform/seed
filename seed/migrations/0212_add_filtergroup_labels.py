# Generated by Django 3.2.18 on 2023-12-19 16:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0211_auto_20240109_1348"),
    ]

    operations = [
        migrations.AddField(
            model_name="filtergroup",
            name="and_labels",
            field=models.ManyToManyField(related_name="and_filter_groups", to="seed.StatusLabel"),
        ),
        migrations.AddField(
            model_name="filtergroup",
            name="exclude_labels",
            field=models.ManyToManyField(related_name="exclude_filter_groups", to="seed.StatusLabel"),
        ),
        migrations.AddField(
            model_name="filtergroup",
            name="or_labels",
            field=models.ManyToManyField(related_name="or_filter_groups", to="seed.StatusLabel"),
        ),
    ]
