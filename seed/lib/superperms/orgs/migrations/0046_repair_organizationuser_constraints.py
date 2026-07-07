# Generated manually to repair databases that recorded old orgs migrations
# without retaining the OrganizationUser table constraints.

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
                    WHERE conrelid = 'orgs_organizationuser'::regclass
                      AND contype = 'p'
                ) THEN
                    ALTER TABLE orgs_organizationuser
                    ADD CONSTRAINT orgs_organizationuser_pkey PRIMARY KEY (id);
                END IF;

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
