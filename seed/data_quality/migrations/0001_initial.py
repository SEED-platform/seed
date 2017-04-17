# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Rules',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field', models.CharField(max_length=200)),
                ('enabled', models.BooleanField(default=True)),
                ('category', models.IntegerField(choices=[(0, b'Missing Matching Field'), (1, b'Missing Values'), (2, b'In-range Checking'), (3, b'Data Type Check')])),
                ('type', models.IntegerField(null=True, choices=[(0, b'number'), (1, b'string'), (2, b'date'), (3, b'year')])),
                ('min', models.FloatField(null=True)),
                ('max', models.FloatField(null=True)),
                ('severity', models.IntegerField(choices=[(0, b'error'), (1, b'warning')])),
                ('units', models.CharField(max_length=100, blank=True)),
                ('org', models.ForeignKey(to='orgs.Organization')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
