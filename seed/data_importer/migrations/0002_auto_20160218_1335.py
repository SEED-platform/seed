# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importrecord',
            name='mcm_version',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
