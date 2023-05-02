from django.db import migrations, transaction


@transaction.atomic
def remove_null_taxlot_views(apps, _schema_editor):
    TaxlotView = apps.get_model('seed', 'TaxlotView')

    null_taxlot_views = TaxlotView.objects.filter(taxlot_id=None)

    if null_taxlot_views.count() > 0:
        print(f"FOUND {null_taxlot_views.count()} TAXLOTVIEWS WITH NULL TAXLOTS, REMOVING...")
        null_taxlot_views.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0192_sf_default_account_fields'),
    ]

    operations = [
        migrations.RunPython(remove_null_taxlot_views),
    ]
