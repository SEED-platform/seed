# Generated by Django 1.9.5 on 2016-09-10 00:49

from django.db import migrations


def migrate_property_view_labels(apps, schema_editor):
    # PropertyView = apps.get_model("seed", "PropertyView")
    # PropertyLabels = apps.get_model("seed", "Property_labels")
    # pvs = PropertyView.objects.all()
    # pvls = {
    #     pv.property.pk: pv.labels.all() for pv in pvs if pv.labels.all()
    # }
    # new_labels = []
    # for pk, label_set in pvls.items():
    #     for label in label_set:
    #         new_labels.append(
    #             PropertyLabels(property_id=pk, statuslabel_id=label.pk)
    #         )
    # PropertyLabels.objects.bulk_create(new_labels, batch_size=1000)
    return


def migrate_taxlot_view_labels(apps, schema_editor):
    # TaxLotView = apps.get_model("seed", "TaxLotView")
    # TaxLotLabels = apps.get_model("seed", "TaxLot_labels")
    # tvs = TaxLotView.objects.all()
    # tvls = {
    #     tv.taxlot.pk: tv.labels.all() for tv in tvs if tv.labels.all()
    # }
    # new_labels = []
    # for pk, label_set in tvls.items():
    #     for label in label_set:
    #         new_labels.append(
    #             TaxLotLabels(taxlot_id=pk, statuslabel_id=label.pk)
    #         )
    # TaxLotLabels.objects.bulk_create(new_labels, batch_size=1000)
    return


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0031_auto_20160913_0001"),
    ]

    operations = [
        migrations.RunPython(migrate_property_view_labels),
        migrations.RunPython(migrate_taxlot_view_labels),
    ]
