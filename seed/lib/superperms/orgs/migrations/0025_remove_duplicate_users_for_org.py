from django.db import migrations
from django.db.models import Count, Max


def remove_duplicate_users_for_org(apps, _schema_editor):
    OrganizationUser = apps.get_model('orgs', 'OrganizationUser')
    unique_fields = ['organization_id', 'user_id']

    duplicate_groups = OrganizationUser.objects.values(*unique_fields) \
        .order_by() \
        .annotate(count=Count('user_id')) \
        .filter(count__gt=1)

    for duplicate_group in duplicate_groups:
        duplicates = OrganizationUser.objects.filter(**{x: duplicate_group[x] for x in unique_fields}) \
            .order_by('-role_level', 'id')

        # Keep the oldest record with the highest role_level
        id_to_keep = duplicates[0].id
        duplicates.exclude(id=id_to_keep).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0024_salesforce_configurations'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_users_for_org),
    ]
