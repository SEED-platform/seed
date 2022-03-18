# Manually created on 2021-09-23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0150_auto_20210922_1909'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE "landing_seeduser" ALTER COLUMN "default_custom_columns" TYPE jsonb;'),
        migrations.RunSQL('ALTER TABLE "landing_seeduser" ALTER COLUMN "default_building_detail_custom_columns" TYPE jsonb;'),
    ]
