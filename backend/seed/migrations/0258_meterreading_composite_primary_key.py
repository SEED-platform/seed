import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Replace MeterReading's fake `start_time` primary key with a real composite primary key.

    0103_auto_20190505_0731 dropped the `start_time` primary key constraint so seed_meterreading could become a
    hypertable, but Django still treated `start_time` as the primary key. Because start_time isn't unique, saving or
    deleting a single reading by pk affected every meter's reading with the same start_time. The natural key
    (meter, start_time, end_time) is already unique and contains the hypertable's time column, so it becomes the
    primary key. Django can't add a composite primary key to an existing table, so it's added with SQL.
    """

    dependencies = [
        ("seed", "0257_column_name_constraints"),
    ]

    operations = [
        # Primary key columns can't be null, and a reading without a meter is unreachable anyway
        migrations.RunSQL("DELETE FROM seed_meterreading WHERE meter_id IS NULL"),
        migrations.AlterField(
            model_name="meterreading",
            name="meter",
            field=models.ForeignKey(
                db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name="meter_readings", to="seed.meter"
            ),
        ),
        migrations.AlterField(
            model_name="meterreading",
            name="start_time",
            field=models.DateTimeField(),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE seed_meterreading ADD CONSTRAINT seed_meterreading_pkey PRIMARY KEY (meter_id, start_time, end_time)"
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="meterreading",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "meter", "start_time", "end_time", blank=True, editable=False, primary_key=True, serialize=False
                    ),
                ),
            ],
        ),
        # Redundant with the primary key
        migrations.AlterUniqueTogether(
            name="meterreading",
            unique_together=set(),
        ),
    ]
