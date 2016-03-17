# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0003_seeduser_default_building_detail_custom_columns'),
    ]

    operations = [
        migrations.AlterField(
            model_name='seeduser',
            name='default_organization',
            field=models.ForeignKey(related_name='default_users', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='orgs.Organization', null=True),
            preserve_default=True,
        ),
    ]
