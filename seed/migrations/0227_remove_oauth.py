from django.db import migrations

# remove the oauth2 tables from the database

DROP_OAUTH_TABLES = """
    DROP TABLE IF EXISTS oauth2_jwt_provider_publickey CASCADE;
    DROP TABLE IF EXISTS oauth2_provider_accesstoken CASCADE;
    DROP TABLE IF EXISTS oauth2_provider_application CASCADE;
    DROP TABLE IF EXISTS oauth2_provider_grant CASCADE;
    DROP TABLE IF EXISTS oauth2_provider_refreshtoken CASCADE;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0226_rehash"),
    ]

    operations = [
        migrations.RunSQL(DROP_OAUTH_TABLES),
    ]
