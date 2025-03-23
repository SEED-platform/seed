import json
import locale
import re
import string

from django.db import migrations


def _snake_case(display_name):
    """
    Convert the BuildingSync measure display names into reasonable snake_case for storing into
    database.

    :param display_name: BuidingSync measure displayname
    :return: string
    """
    str_re = re.compile(f"[{re.escape(string.punctuation)}]")
    str = str_re.sub(" ", display_name)
    str = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", str)
    str = re.sub("([a-z0-9])([A-Z])", r"\1_\2", str).lower()
    return re.sub(" +", "_", str)

def populate_measures(apps, organization_id, schema_type="BuildingSync", schema_version="2.6.0"):
    """
    Populate the list of measures from BuildingSync version 2.6.0

    :param organization_id: integer, ID of the organization to populate measures
    :return:
    """
    filename = "seed/building_sync/lib/enumerations.json"
    with open(filename, encoding=locale.getpreferredencoding(False)) as f:
        data = json.load(f)

        Measure = apps.get_model("seed", "Measure")

        for datum in data:
            # "name": "MeasureName",
            # "sub_name": "AdvancedMeteringSystems",
            # "documentation": "Advanced Metering Systems",
            # "enumerations": [
            #                     "Install advanced metering systems",
            #                     "Clean and/or repair",
            #                     "Implement training and/or documentation",
            #                     "Upgrade operating protocols, calibration, and/or sequencing",
            #                     "Other"
            #                 ],
            if datum["name"] == "MeasureName":
                for enum in datum["enumerations"]:
                    Measure.objects.get_or_create(
                        organization_id=organization_id,
                        category=_snake_case(datum["sub_name"]),
                        category_display_name=datum["documentation"],
                        name=_snake_case(enum),
                        display_name=enum,
                        schema_type=schema_type,
                        schema_version=schema_version,
                    )


def forwards(apps, schema_editor):
    # process the measures table with changes from BuildingSync v2.6.0
    Organization = apps.get_model("orgs", "Organization")

    # find all organizations
    for c in Organization.objects.all():
        print(f"Org: {c.name}, Name: {c.id}")

        # call populate_measures
        populate_measures(apps, c.id, '2.6.0')


class Migration(migrations.Migration):
    dependencies = [
        ('orgs', '0041_add_at_tracking_fields'),
        ("seed", "0242_add_meter_types"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='measure',
            unique_together={('organization', 'category', 'name', 'schema_version')},
        ),
        migrations.RunPython(forwards)
    ]

