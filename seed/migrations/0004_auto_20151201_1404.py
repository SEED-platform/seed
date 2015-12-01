# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0003_auto_20151105_1539'),
    ]

    operations = [
        migrations.AlterField(
            model_name='statuslabel',
            name='color',
            field=models.CharField(default=b'green', max_length=30, verbose_name='compliance_type', choices=[(b'red', 'red'), (b'blue', 'blue'), (b'light blue', 'light blue'), (b'green', 'green'), (b'white', 'white'), (b'orange', 'orange'), (b'gray', 'gray')]),
            preserve_default=True,
        ),
    ]
