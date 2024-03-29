from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('landing', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seeduser',
            name='default_custom_columns',
            field=models.JSONField(default={}),
            preserve_default=True,
        ),
    ]
