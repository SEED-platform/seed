import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Convert seed_sensorreading to a TimescaleDB hypertable partitioned on `timestamp`.

    Every unique index on a hypertable must contain the time column, so the unused `id` primary key is replaced with
    the natural key (sensor, timestamp), which also replaces the unique_together constraint and the sensor_id index.
    Django can't add a composite primary key to an existing table, so it's added with SQL. `migrate_data` moves the
    existing rows into chunks while holding an exclusive lock on the table.
    """

    dependencies = [
        ("seed", "0258_meterreading_composite_primary_key"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sensorreading",
            name="id",
        ),
        migrations.AlterField(
            model_name="sensorreading",
            name="sensor",
            field=models.ForeignKey(
                db_index=False, on_delete=django.db.models.deletion.CASCADE, related_name="sensor_readings", to="seed.sensor"
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    'ALTER TABLE seed_sensorreading ADD CONSTRAINT seed_sensorreading_pkey PRIMARY KEY (sensor_id, "timestamp")'
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="sensorreading",
                    name="pk",
                    field=models.CompositePrimaryKey("sensor", "timestamp", blank=True, editable=False, primary_key=True, serialize=False),
                ),
            ],
        ),
        # Redundant with the primary key
        migrations.AlterUniqueTogether(
            name="sensorreading",
            unique_together=set(),
        ),
        # The primary key covers per-sensor time range queries, so TimescaleDB's default time index isn't needed
        migrations.RunSQL(
            "SELECT create_hypertable('seed_sensorreading', by_range('timestamp'), create_default_indexes => false, migrate_data => true)"
        ),
    ]
