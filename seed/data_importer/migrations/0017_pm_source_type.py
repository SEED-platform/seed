from __future__ import unicode_literals

from django.db import migrations

from seed.models import PORTFOLIO_RAW, SEED_DATA_SOURCES, SENSOR_METADATA


def fix_source_type(apps, schema_editor):
    import_files = apps.get_model('data_importer', 'ImportFile').objects

    # Fix ImportFile `source_type` fields that incorrectly list ESPM imports as Assessed imports
    import_files.filter(source_program='PortfolioManager').update(
        source_type=SEED_DATA_SOURCES[PORTFOLIO_RAW][1]
    )

    # Rename `SensorMetaData` to `SensorMetadata` for consistency
    import_files.filter(source_type='SensorMetaData').update(
        source_type=SEED_DATA_SOURCES[SENSOR_METADATA][1]
    )


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0016_auto_20220119_1347'),
    ]

    operations = [
        migrations.RunPython(fix_source_type),
    ]
