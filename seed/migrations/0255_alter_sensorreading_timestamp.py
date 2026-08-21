import timescale.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0254_repair_missing_primary_keys"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sensorreading",
            name="timestamp",
            field=timescale.db.models.fields.TimescaleDateTimeField(interval="7 days"),
        ),
    ]
