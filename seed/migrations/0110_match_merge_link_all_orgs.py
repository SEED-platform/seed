# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction
from seed.utils.match import whole_org_match_merge


def forwards(apps, schema_editor):
    Organization = apps.get_model("orgs", "organization")

    for org in Organization.objects.all():
        whole_org_match_merge(org.id)
    print('summary of full match merge link round')


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0109_column_is_matching_criteria'),
    ]

    operations = [
        # migrations.RunPython(forwards),
    ]
