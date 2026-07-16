from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0012_auto_20151222_1031"),
    ]

    operations = [
        migrations.AlterField(
            model_name="attributeoption",
            name="value",
            field=models.TextField(),
            preserve_default=True,
        ),
    ]
