# Generated by Django 1.9.5 on 2017-05-22 19:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0065_auto_20170518_0854"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rule",
            name="severity",
            field=models.IntegerField(choices=[(0, b"error"), (1, b"warning")], default=0),
        ),
    ]
