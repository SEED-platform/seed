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
# Each ALTER TABLE is guarded by pg_constraint checks so this migration is safe
# on databases that already have the expected constraints.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0045_organization_max_data_charted"),
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

                -- Required for foreign keys that reference orgs_organizationuser(id).
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'orgs_organizationuser'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE orgs_organizationuser
                    ADD CONSTRAINT orgs_organizationuser_pkey PRIMARY KEY (id);
                END IF;

                -- Restores the model-level uniqueness guarantee added in orgs 0026.
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conrelid = 'orgs_organizationuser'::regclass
                      AND conname = 'unique_user_for_organization'
                ) THEN
                    ALTER TABLE orgs_organizationuser
                    ADD CONSTRAINT unique_user_for_organization UNIQUE (user_id, organization_id);
                END IF;
            END
            $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
