from __future__ import unicode_literals

from django.db import migrations

from seed.models import PORTFOLIO_RAW, SEED_DATA_SOURCES


def fix_source_type(apps, schema_editor):
    for import_file in apps.get_model('data_importer', 'ImportFile').objects.filter(source_program='PortfolioManager'):
        import_file.source_type = SEED_DATA_SOURCES[PORTFOLIO_RAW][1]
        import_file.save()


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0016_auto_20220119_1347'),
    ]

    operations = [
        migrations.RunPython(fix_source_type),
    ]
