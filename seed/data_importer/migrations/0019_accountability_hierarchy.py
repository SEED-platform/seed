# Generated by Django 3.2.23 on 2024-03-08 06:05

import django.db.models.deletion
from django.db import migrations, models, transaction


@transaction.atomic
def set_import_records_ali(apps, schema_editor):
    ImportRecord = apps.get_model('data_importer', 'ImportRecord')
    AccessLevelInstance = apps.get_model('orgs', 'AccessLevelInstance')

    if ImportRecord.objects.filter(super_organization=None).exists():
        raise ValueError("Some ImportRecords have no super_organization, and are orphaned. This shouldn't have happened and these ImportRecords cannot be migrated. Please add a super_organization or delete the orphaned ImportRecords and try again.")

    root_alis = {ali.organization_id: ali for ali in AccessLevelInstance.objects.filter(depth=1)}

    for import_record in ImportRecord.objects.all().iterator():
        import_record.access_level_instance = root_alis[import_record.super_organization_id]
        import_record.save(update_fields=['access_level_instance'])


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0030_accountability_hierarchy'),
        ('data_importer', '0018_importfile_multiple_cycle_upload'),
    ]

    operations = [
        migrations.AddField(
            model_name='importrecord',
            name='access_level_instance',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='import_record', to='orgs.accesslevelinstance'),
        ),
        migrations.RunPython(set_import_records_ali, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='importrecord',
            name='access_level_instance',
            field=models.ForeignKey(null=False, on_delete=django.db.models.deletion.CASCADE, related_name='import_record', to='orgs.accesslevelinstance'),
        ),
    ]