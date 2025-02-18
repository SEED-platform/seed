# Generated by Django 1.9.5 on 2016-09-12 18:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0030_column_table_name"),
    ]

    operations = [
        migrations.RenameField(
            model_name="propertystate",
            old_name="building_home_energy_score_identifier",
            new_name="home_energy_score_id",
        ),
        migrations.RenameField(
            model_name="propertystate",
            old_name="jurisdiction_property_identifier",
            new_name="jurisdiction_property_id",
        ),
        migrations.RenameField(
            model_name="propertystate",
            old_name="super_organization",
            new_name="organization",
        ),
        migrations.RenameField(
            model_name="taxlotstate",
            old_name="address",
            new_name="address_line_1",
        ),
        migrations.RenameField(
            model_name="taxlotstate",
            old_name="jurisdiction_taxlot_identifier",
            new_name="jurisdiction_tax_lot_id",
        ),
        migrations.RemoveField(
            model_name="propertystate",
            name="building_portfolio_manager_identifier",
        ),
        migrations.AddField(
            model_name="taxlotstate",
            name="address_line_2",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
