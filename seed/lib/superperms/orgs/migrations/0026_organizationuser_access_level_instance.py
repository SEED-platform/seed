# Generated by Django 3.2.18 on 2023-04-13 21:56

from django.db import migrations, models
import django.db.models.deletion
from django.db import transaction


@transaction.atomic
def assign_users_to_root_acces_level(apps, schema_editor):
    OrganizationUser = apps.get_model('orgs', 'OrganizationUser')
    AccessLevelInstance = apps.get_model('orgs', 'AccessLevelInstance')

    users = OrganizationUser.objects.all()
    for user in users:
        root = AccessLevelInstance.objects.get(depth=1, organization=user.organization)
        user.access_level_instance = root
        user.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0025_auto_20230413_1250'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationuser',
            name='access_level_instance',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='orgs.accesslevelinstance', related_name="users"),
        ),
        migrations.RunPython(assign_users_to_root_acces_level, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='organizationuser',
            name='access_level_instance',
            field=models.ForeignKey(null=False, on_delete=django.db.models.deletion.CASCADE, to='orgs.accesslevelinstance', related_name="users"),
        )
    ]