# Generated by Django 1.11.16 on 2018-11-07 20:31

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0096_auto_20181107_0904"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="attributeoption",
            name="building_variant",
        ),
        migrations.AlterUniqueTogether(
            name="buildingattributevariant",
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name="buildingattributevariant",
            name="building_snapshot",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="address_line_1_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="address_line_2_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="best_guess_canonical_building",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="block_number_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="building_certification_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="building_count_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="canonical_building",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="canonical_for_ds",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="children",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="city_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="conditioned_floor_area_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="custom_id_1_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="district_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="duplicate",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="energy_alerts_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="energy_score_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="generation_date_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="gross_floor_area_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="import_file",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="last_modified_by",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="lot_number_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="occupied_floor_area_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="owner_address_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="owner_city_state_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="owner_email_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="owner_postal_code_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="owner_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="owner_telephone_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="pm_property_id_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="postal_code_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="property_name_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="property_notes_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="recent_sale_date_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="release_date_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="site_eui_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="site_eui_weather_normalized_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="source_eui_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="source_eui_weather_normalized_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="space_alerts_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="state_province_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="super_organization",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="tax_lot_id_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="use_description_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="year_built_source",
        ),
        migrations.RemoveField(
            model_name="buildingsnapshot",
            name="year_ending_source",
        ),
        migrations.RemoveField(
            model_name="canonicalbuilding",
            name="canonical_snapshot",
        ),
        migrations.RemoveField(
            model_name="canonicalbuilding",
            name="labels",
        ),
        migrations.RemoveField(
            model_name="custombuildingheaders",
            name="super_organization",
        ),
        migrations.RemoveField(
            model_name="enum",
            name="enum_values",
        ),
        migrations.RemoveField(
            model_name="column",
            name="enum",
        ),
        migrations.DeleteModel(
            name="Enum",
        ),
        migrations.DeleteModel(
            name="EnumValue",
        ),
        migrations.DeleteModel(
            name="AttributeOption",
        ),
        migrations.DeleteModel(
            name="BuildingAttributeVariant",
        ),
        migrations.DeleteModel(
            name="BuildingSnapshot",
        ),
        migrations.DeleteModel(
            name="CanonicalBuilding",
        ),
        migrations.DeleteModel(
            name="CustomBuildingHeaders",
        ),
        # Make sure that these other tables get removed too
        migrations.RunSQL("DROP TABLE IF EXISTS audit_logs_auditlog;"),
        migrations.RunSQL("DROP TABLE IF EXISTS seed_canonicalbuilding_labels;"),
        migrations.RunSQL("DROP TABLE IF EXISTS seed_buildingsnapshot_children;"),
    ]
