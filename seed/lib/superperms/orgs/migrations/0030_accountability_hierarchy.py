# Generated by Django 3.2.23 on 2024-03-08 06:05

import django.db.models.deletion
from django.db import migrations, models, transaction


@transaction.atomic
def create_root_access_levels(apps, schema_editor):
    Organization = apps.get_model('orgs', 'Organization')
    AccessLevelInstance = apps.get_model('orgs', 'AccessLevelInstance')

    for i, org in enumerate(Organization.objects.all()):
        org.access_level_names = [org.name]
        org.save()

        AccessLevelInstance.objects.create(
            tree_id=i,
            organization=org,
            name='root',
            path={org.access_level_names[0]: 'root'},
            depth=1,
            lft=1,
            rgt=2,
        )


@transaction.atomic
def assign_users_to_root_access_level(apps, schema_editor):
    OrganizationUser = apps.get_model('orgs', 'OrganizationUser')
    AccessLevelInstance = apps.get_model('orgs', 'AccessLevelInstance')

    root_alis = {ali.organization_id: ali for ali in AccessLevelInstance.objects.filter(depth=1)}

    for user in OrganizationUser.objects.all():
        user.access_level_instance = root_alis[user.organization_id]
        user.save(update_fields=['access_level_instance'])


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0029_auto_20240105_1257'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='access_level_names',
            field=models.JSONField(default=list),
        ),
        migrations.CreateModel(
            name='AccessLevelInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lft', models.PositiveIntegerField(db_index=True)),
                ('rgt', models.PositiveIntegerField(db_index=True)),
                ('tree_id', models.PositiveIntegerField(db_index=True)),
                ('depth', models.PositiveIntegerField(db_index=True)),
                ('name', models.CharField(max_length=100)),
                ('path', models.JSONField()),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='orgs.organization')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='organizationuser',
            name='access_level_instance',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='users', to='orgs.accesslevelinstance'),
        ),
        migrations.RunPython(create_root_access_levels),
        migrations.RunPython(assign_users_to_root_access_level, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='organizationuser',
            name='access_level_instance',
            field=models.ForeignKey(null=False, on_delete=django.db.models.deletion.CASCADE, related_name='users', to='orgs.accesslevelinstance'),
        )
    ]