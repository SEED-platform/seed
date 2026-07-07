# Generated manually to repair databases that recorded prior migrations
# without retaining primary key constraints needed by later foreign keys.

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
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'orgs_organization'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE orgs_organization
                    ADD CONSTRAINT orgs_organization_pkey PRIMARY KEY (id);
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'seed_cycle'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE seed_cycle
                    ADD CONSTRAINT seed_cycle_pkey PRIMARY KEY (id);
                END IF;

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
