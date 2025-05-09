# Generated by Django 3.2.13 on 2022-05-27 15:05

from django.db import migrations, models


def forwards(apps, schema_editor):
    Column = apps.get_model("seed", "Column")
    Organization = apps.get_model("orgs", "Organization")

    new_db_fields = [
        {
            "column_name": "property_timezone",
            "table_name": "PropertyState",
            "display_name": "Property Time Zone",
            "column_description": "Time zone of the property",
            "data_type": "string",
        }
    ]

    # Go through all the organizations
    for org in Organization.objects.all():
        for new_db_field in new_db_fields:
            columns = Column.objects.filter(
                organization_id=org.id,
                table_name=new_db_field["table_name"],
                column_name=new_db_field["column_name"],
                is_extra_data=False,
            )

            if not columns.count():
                new_db_field["organization_id"] = org.id
                Column.objects.create(**new_db_field)
            elif columns.count() == 1:
                # If the column exists, then just update the display_name and data_type if empty
                c = columns.first()
                if c.display_name is None or c.display_name == "":
                    c.display_name = new_db_field["display_name"]
                if c.data_type is None or c.data_type in ("", "None"):
                    c.data_type = new_db_field["data_type"]
                c.save()
            else:
                print("  More than one column returned")


class Migration(migrations.Migration):
    dependencies = [
        ("seed", "0165_column_column_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="propertystate",
            name="property_timezone",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.RunPython(forwards),
    ]
