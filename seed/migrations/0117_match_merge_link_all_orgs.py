# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from seed.utils.match import whole_org_match_merge_link


def forwards(apps, schema_editor):
    Organization = apps.get_model("orgs", "organization")

    for org in Organization.objects.all():
        whole_org_match_merge_link(org.id, 'PropertyState')
        whole_org_match_merge_link(org.id, 'TaxLotState')


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0116_auto_20191219_1606'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
