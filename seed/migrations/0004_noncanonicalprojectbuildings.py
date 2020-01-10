# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0003_auto_20151105_1539'),
    ]

    operations = [
        migrations.CreateModel(
            name='NonCanonicalProjectBuildings',
            fields=[
                ('projectbuilding', models.ForeignKey(on_delete=models.deletion.CASCADE, primary_key=True, serialize=False, to='seed.ProjectBuilding')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
