# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0003_auto_20150819_0811'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='importrecord',
            name='organization',
        ),
    ]
