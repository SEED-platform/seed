# Generated manually to repair production databases that recorded earlier orgs
# migrations as applied without retaining the database constraints those
# migrations should have created.
#
# Later seed migrations add foreign keys that reference orgs_organization and
# orgs_organizationuser. PostgreSQL requires the referenced columns to be backed
# by a primary key or unique constraint, so those later migrations fail if a
# database is missing these constraints even though Django thinks the historical
# migrations already ran.
#
# All repairs are idempotent (guarded by pg_catalog checks), so this migration is
# safe on databases that already have the expected constraints.

from django.db import migrations

from seed.utils.migrations import add_missing_unique_constraint_sql, repair_all_missing_primary_keys_sql


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0045_organization_max_data_charted"),
    ]

    operations = [
        # Restore missing "id" primary keys on every orgs_* table.
        migrations.RunSQL(
            sql=repair_all_missing_primary_keys_sql("orgs_"),
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Restore the model-level uniqueness guarantee added in orgs 0026.
        migrations.RunSQL(
            sql=add_missing_unique_constraint_sql(
                "orgs_organizationuser",
                "unique_user_for_organization",
                "user_id",
                "organization_id",
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
