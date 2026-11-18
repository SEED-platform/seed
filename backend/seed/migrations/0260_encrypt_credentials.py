# Generated manually to encrypt the Salesforce credentials. The Salesforce password was previously only signed (and
# readable), and the Salesforce security token and the Portfolio Salesforce client secret were stored in plaintext.
# The credentials stored on organizations are encrypted by orgs migration 0048.
#
# The columns are widened since encrypted values are longer than the plaintext. See
# `seed.utils.encrypt.convert_legacy_secret` for how each stored value is converted.

from django.db import migrations, models

from seed.utils.encrypt import encrypt_column

# The model, field, and whether the column held legacy signed values rather than plaintext
SECRET_FIELDS = [
    ("SalesforceConfig", "password", True),
    ("SalesforceConfig", "security_token", False),
    ("BBSalesforceConfig", "client_secret", False),
]


def encrypt_credentials(apps, schema_editor):
    for model_name, field_name, signed in SECRET_FIELDS:
        encrypt_column(apps.get_model("seed", model_name), field_name, signed=signed)


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0259_sensorreading_hypertable"),
    ]

    operations = [
        migrations.AlterField(
            model_name="salesforceconfig",
            name="password",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="salesforceconfig",
            name="security_token",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="bbsalesforceconfig",
            name="client_secret",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(encrypt_credentials),
    ]
