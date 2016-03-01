# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0012_auto_20151222_1031'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attributeoption',
            name='value',
            field=models.TextField(),
            preserve_default=True,
        ),
    ]
