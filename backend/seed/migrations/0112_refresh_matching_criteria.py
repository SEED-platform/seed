from django.db import migrations, transaction


def forwards(apps, schema_editor):
    Column = apps.get_model("seed", "Column")

    with transaction.atomic():
        propertystate_matching_criteria = [
            "address_line_1",  # Technically this was normalized_address, but matching logic handles this as such
            "custom_id_1",
            "pm_property_id",
            "ubid",
        ]

        taxlotstate_matching_criteria = [
            "address_line_1",  # Technically this was normalized_address, but matching logic handles this as such
            "custom_id_1",
            "jurisdiction_tax_lot_id",
            "ulid",
        ]

        # Ensure ONLY initial matching criteria is set to True
        Column.objects.filter(table_name="PropertyState", column_name__in=propertystate_matching_criteria).update(is_matching_criteria=True)
        Column.objects.filter(table_name="PropertyState").exclude(column_name__in=propertystate_matching_criteria).update(
            is_matching_criteria=False
        )

        Column.objects.filter(table_name="TaxLotState", column_name__in=taxlotstate_matching_criteria).update(is_matching_criteria=True)
        Column.objects.filter(table_name="TaxLotState").exclude(column_name__in=taxlotstate_matching_criteria).update(
            is_matching_criteria=False
        )

        # Also, the Column records NOT attached to any table type should definitely NOT be matching criteria.
        Column.objects.filter(table_name="").update(is_matching_criteria=False)


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0111_rehash"),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
