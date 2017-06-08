# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.jsonb


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0002_buildingsnapshot_duplicate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='buildingsnapshot',
            name='extra_data',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='buildingsnapshot',
            name='extra_data_sources',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='custombuildingheaders',
            name='building_headers',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
            preserve_default=True,
        ),
    ]
