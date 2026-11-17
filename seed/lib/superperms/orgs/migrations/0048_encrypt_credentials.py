# Generated manually to encrypt the third-party credentials stored on organizations. The Audit Template password was
# previously only signed (and readable), and the Audit Template organization token and the BETTER and MapQuest API
# keys were stored in plaintext. The Salesforce credentials are encrypted by seed migration 0260.
#
# The columns are widened since encrypted values are longer than the plaintext. See
# `seed.utils.encrypt.convert_legacy_secret` for how each stored value is converted. An Audit Template organization
# token of "False" (saved when the token was omitted) is cleared.

from django.db import migrations, models

from seed.utils.encrypt import encrypt_column

# Whether each column held legacy signed values rather than plaintext
SECRET_FIELDS = {
    "audit_template_password": True,
    "at_organization_token": False,
    "better_analysis_api_key": False,
    "mapquest_api_key": False,
}


def encrypt_credentials(apps, schema_editor):
    Organization = apps.get_model("orgs", "Organization")
    # the settings view stored an omitted Audit Template organization token as "False"
    cleared = Organization.objects.filter(at_organization_token="False").update(at_organization_token="")
    if cleared:
        print(f'orgs.Organization.at_organization_token: cleared {cleared} values of "False" (saved when the token was omitted)')
    for field_name, signed in SECRET_FIELDS.items():
        encrypt_column(Organization, field_name, signed=signed)


class Migration(migrations.Migration):
    dependencies = [
        ("orgs", "0047_delete_cross_organization_memberships"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="audit_template_password",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="organization",
            name="at_organization_token",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="organization",
            name="better_analysis_api_key",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="organization",
            name="mapquest_api_key",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(encrypt_credentials),
    ]
