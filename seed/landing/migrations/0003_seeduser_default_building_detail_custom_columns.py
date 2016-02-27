# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_pgjson.fields


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0002_auto_20151105_1539'),
    ]

    operations = [
        migrations.AddField(
            model_name='seeduser',
            name='default_building_detail_custom_columns',
            field=django_pgjson.fields.JsonField(default={}),
            preserve_default=True,
        ),
    ]
