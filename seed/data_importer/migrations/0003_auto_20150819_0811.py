# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0002_auto_20150711_2103'),
    ]

    operations = [
        migrations.AlterField(
            model_name='validationrule',
            name='passes',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
