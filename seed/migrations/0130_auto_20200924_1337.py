# Manually generated on 2020-09-24 13:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0129_auto_20200828_0610'),
    ]

    operations = [
        migrations.RunSQL('ALTER TABLE "seed_taxlotstate" ALTER COLUMN "extra_data" TYPE jsonb;'),
        migrations.RunSQL('ALTER TABLE "seed_propertystate" ALTER COLUMN "extra_data" TYPE jsonb;'),
    ]
