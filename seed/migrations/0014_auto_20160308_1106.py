# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0013_auto_20160225_1213'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='schema',
            name='columns',
        ),
        migrations.RemoveField(
            model_name='schema',
            name='organization',
        ),
        migrations.DeleteModel(
            name='Schema',
        ),
    ]
