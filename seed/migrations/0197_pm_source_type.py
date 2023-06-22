from django.db import migrations

from seed.models import ASSESSED_BS, ASSESSED_RAW, PORTFOLIO_BS, PORTFOLIO_RAW


def fix_source_type(apps, schema_editor):
    # Fix PropertyState `source_type` fields that incorrectly list ESPM imports as Assessed imports
    pm_imports = apps.get_model('data_importer', 'ImportFile').objects.filter(source_program='PortfolioManager')
    property_states = apps.get_model('seed', 'PropertyState').objects.filter(
        import_file__in=pm_imports,
        source_type__isnull=False,
    )

    property_states.filter(source_type=ASSESSED_RAW).update(source_type=PORTFOLIO_RAW)
    property_states.filter(source_type=ASSESSED_BS).update(source_type=PORTFOLIO_BS)


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0196_alter_source_types'),
    ]

    operations = [
        migrations.RunPython(fix_source_type),
    ]
