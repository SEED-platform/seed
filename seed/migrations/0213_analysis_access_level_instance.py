# Generated by Django 3.2.20 on 2023-08-22 02:07

import django.db.models.deletion
from django.db import migrations, models, transaction


@transaction.atomic
def set_analysis_ali(apps, schema_editor):
    Analysis = apps.get_model('seed', 'Analysis')
    AccessLevelInstance = apps.get_model('orgs', 'AccessLevelInstance')
    OrganizationUser = apps.get_model('orgs', 'OrganizationUser')

    analyses = Analysis.objects.all()
    for analysis in analyses:
        user = analysis.user
        org = analysis.organization

        if org is None:
            raise ValueError(f"Analysis with pk {analysis.pk} has no organization, and is thus orphaned. This shouldn't have happened and this Analysis cannot be migrated. Please add a oganization or delete the analysis and try again.")

        if user is not None:
            try:
                org_user = OrganizationUser.objects.get(organization=org, user=user)
                ali = org_user.access_level_instance
            except OrganizationUser.DoesNotExist:
                raise ValueError(f"Analysis with pk {analysis.pk} has organization with pk {org.pk} and user with pk {user.pk}. The user is not a part of this org, which is weird.")
        else:
            ali = AccessLevelInstance.objects.get(organization=org, depth=1)

        analysis.access_level_instance = ali
        analysis.save()


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0029_auto_20230413_1250'),
        ('seed', '0212_auto_20230623_1556'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysis',
            name='access_level_instance',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='analyses', to='orgs.accesslevelinstance'),
        ),
        migrations.RunPython(set_analysis_ali, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='analysis',
            name='access_level_instance',
            field=models.ForeignKey(null=False, on_delete=django.db.models.deletion.CASCADE, related_name='analyses', to='orgs.accesslevelinstance'),
        )
    ]