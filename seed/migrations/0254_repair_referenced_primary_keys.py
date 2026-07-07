# Generated manually to repair production databases that recorded prior seed
# migrations as applied without retaining primary key constraints on referenced
# tables.
#
# This migration exists after seed 0253 because some databases may already have
# seed 0250 marked as applied. Editing seed 0250 can help databases that have not
# reached it yet, but Django will not rerun 0250 on databases that are already
# past it. This follow-up migration repairs that already-migrated state.
#
# The repaired primary keys are required before later migrations can add foreign
# keys to these tables. Each ALTER TABLE is guarded by pg_constraint checks so
# the migration is idempotent on healthy databases.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0046_repair_organizationuser_constraints"),
        ("seed", "0253_allow_empty_filter_groups_on_dataview"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                -- Required for foreign keys that reference orgs_organization(id).
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'orgs_organization'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE orgs_organization
                    ADD CONSTRAINT orgs_organization_pkey PRIMARY KEY (id);
                END IF;

                -- Required for foreign keys that reference seed_cycle(id).
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'seed_cycle'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE seed_cycle
                    ADD CONSTRAINT seed_cycle_pkey PRIMARY KEY (id);
                END IF;

                -- Required for foreign keys that reference seed_goal(id).
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'seed_goal'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE seed_goal
                    ADD CONSTRAINT seed_goal_pkey PRIMARY KEY (id);
                END IF;
            END
            $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
