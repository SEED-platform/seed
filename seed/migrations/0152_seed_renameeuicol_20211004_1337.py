# Manually created

from django.db import migrations


def rename_eui_results_col(apps, schema_editor):
    """Update the diplay name for the column the EUI analysis pipeline creates

    We decided Fractional EUI was a more accurate name b/c some buildings might
    not have complete data for the year...
    """
    Column = apps.get_model("seed", "Column")

    Column.objects.filter(
        is_extra_data=True,
        column_name='analysis_eui',
        table_name='PropertyState'
    ).update(display_name='Fractional EUI (kBtu/sqft)')


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0151_seeduser_20210923_1337'),
    ]

    operations = [
        migrations.RunPython(rename_eui_results_col),
    ]
