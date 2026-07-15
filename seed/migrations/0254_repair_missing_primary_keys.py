# Generated manually to repair production databases that recorded prior seed
# migrations as applied without retaining primary key constraints.
#
# This migration exists after seed 0253 because some databases may already have
# seed 0250 marked as applied. Editing seed 0250 helps databases that have not
# reached it yet, but Django will not rerun 0250 on databases that are already
# past it. This follow-up repairs that already-migrated state.
#
# Rather than enumerate a fixed list of tables (which drifts as models change and
# was the reason earlier repairs were incomplete), this scans for every seed_*
# table that has an "id" column but no primary key and restores it. The repair is
# idempotent (guarded by pg_catalog checks), so it is a no-op on healthy
# databases. Missing primary keys are required before later migrations can add
# foreign keys that reference these tables.

from django.db import migrations

from seed.utils.migrations import repair_all_missing_primary_keys_sql


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0253_allow_empty_filter_groups_on_dataview"),
    ]

    operations = [
        migrations.RunSQL(
            sql=repair_all_missing_primary_keys_sql("seed_"),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
