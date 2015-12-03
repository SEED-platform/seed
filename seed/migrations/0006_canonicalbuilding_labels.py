# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0005_auto_20151201_1510'),
    ]

    operations = [
        migrations.AddField(
            model_name='canonicalbuilding',
            name='labels',
            field=models.ManyToManyField(to='seed.StatusLabel'),
            preserve_default=True,
        ),
    ]
