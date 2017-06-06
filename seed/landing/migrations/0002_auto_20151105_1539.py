# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.jsonb

class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seeduser',
            name='default_custom_columns',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
            preserve_default=True,
        ),
    ]
