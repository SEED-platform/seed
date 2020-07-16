# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, ProgrammingError
from seed.utils.match import whole_org_match_merge_link


def forwards(apps, schema_editor):
    Organization = apps.get_model("orgs", "organization")

    try:
        for org in Organization.objects.all():
            whole_org_match_merge_link(org.id, 'PropertyState')
            whole_org_match_merge_link(org.id, 'TaxLotState')
    except ProgrammingError as err:
        print("""

========== MIGRATION FAILURE ==========

  Please check the instructions at the following URL:
  https://github.com/SEED-platform/seed/blob/develop/docs/source/migrations.rst#version-271

=======================================

""")
        raise err


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0117_columnmappingpreset'),
    ]

    operations = [
        migrations.RunPython(forwards),
    ]
