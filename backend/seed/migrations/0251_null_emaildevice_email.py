from django.db import migrations


def null_otp_email(apps, schema_editor):
    EmailDevice = apps.get_model("otp_email", "EmailDevice")
    EmailDevice.objects.exclude(email__isnull=True).update(email=None)


class Migration(migrations.Migration):
    dependencies = [
        ("otp_email", "0006_add_timestamps"),
        ("seed", "0250_remove_goal_current_cycle_goal_partner_note_and_more"),
    ]

    operations = [
        migrations.RunPython(null_otp_email, migrations.RunPython.noop),
    ]
