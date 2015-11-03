# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0002_buildingsnapshot_duplicate'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='buildingsnapshot',
            options={'ordering': ['-id']},
        ),
        migrations.AlterIndexTogether(
            name='buildingsnapshot',
            index_together=set([('super_organization', 'id')]),
        ),
    ]
