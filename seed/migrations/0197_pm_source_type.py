from django.db import migrations

from seed.models import ASSESSED_RAW, PORTFOLIO_RAW, ASSESSED_BS, PORTFOLIO_BS


def fix_source_type(apps, schema_editor):
    pm_imports = apps.get_model('data_importer', 'ImportFile').objects.filter(source_program='PortfolioManager')
    property_states = apps.get_model('seed', 'PropertyState').objects.filter(
        import_file__in=pm_imports,
        source_type__isnull=False,
    )

    for state in property_states.filter(source_type=ASSESSED_RAW):
        state.source_type = PORTFOLIO_RAW
        state.save()

    for state in property_states.filter(source_type=ASSESSED_BS):
        state.source_type = PORTFOLIO_BS
        state.save()


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0196_alter_columnmapping_source_type'),
    ]

    operations = [
        migrations.RunPython(fix_source_type),
    ]
