from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0007_auto_20151201_1515"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="projectbuilding",
            name="status_label",
        ),
    ]
