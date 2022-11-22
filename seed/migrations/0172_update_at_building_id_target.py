from django.db import migrations
import json


def update_at_building_id(apps, schema_editor):
    Organization = apps.get_model("orgs", "Organization")
    for org in Organization.objects.all():
        bsync_mapping_name = 'BuildingSync v2.0 Defaults'
        profiles = org.columnmappingprofile_set.filter(mappings__contains=[{"to_field": "Audit Template Building Id"}])
        for profile in profiles:
            for mapping in profile.mappings:
                if mapping['to_field'] == "Audit Template Building Id":
                    mapping['to_field'] = "audit_template_building_id"
            profile.save(update_fields=['mappings'])


def backwards(apps, schema_editor):
    Organization = apps.get_model("orgs", "Organization")
    for org in Organization.objects.all():
        bsync_mapping_name = 'BuildingSync v2.0 Defaults'
        profiles = org.columnmappingprofile_set.filter(mappings__contains=[{"to_field": "audit_template_building_id"}])
        for profile in profiles:
            for mapping in profile.mappings:
                if mapping['to_field'] == "audit_template_building_id":
                    mapping['to_field'] = "Audit Template Building Id"
            profile.save(update_fields=['mappings'])


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0171_auto_20220628_2059'),
    ]

    operations = [
        migrations.RunPython(update_at_building_id, backwards),
    ]
