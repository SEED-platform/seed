# Generated by Django 1.9.5 on 2017-01-18 21:48

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0045_auto_20170112_1233"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertystate",
            name="merge_state",
            field=models.IntegerField(choices=[(0, b"Unknown"), (1, b"Orphaned as result of merge"), (1, b"Merged Record")], default=0),
        ),
        migrations.AddField(
            model_name="taxlotstate",
            name="merge_state",
            field=models.IntegerField(choices=[(0, b"Unknown"), (1, b"Orphaned as result of merge"), (1, b"Merged Record")], default=0),
        ),
    ]
