# Generated by Django 3.2.25 on 2024-04-19 20:19

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("landing", "0007_auto_20181107_0904"),
    ]

    operations = [
        migrations.AddField(
            model_name="seeduser",
            name="prompt_2fa",
            field=models.BooleanField(default=True),
        ),
    ]