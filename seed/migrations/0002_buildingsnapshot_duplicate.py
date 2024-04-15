from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="buildingsnapshot",
            name="duplicate",
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="+", blank=True, to="seed.BuildingSnapshot", null=True),
            preserve_default=True,
        ),
    ]
