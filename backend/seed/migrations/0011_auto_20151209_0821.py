from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0010_auto_20151204_1337"),
    ]

    operations = [
        migrations.AlterField(
            model_name="statuslabel",
            name="super_organization",
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name="labels",
                verbose_name="SeedOrg",
                blank=True,
                to="orgs.Organization",
                null=True,
            ),
            preserve_default=True,
        ),
    ]
