# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0012_auto_20151222_1031'),
    ]

    operations = [
        migrations.CreateModel(
            name='GreenButtonBatchRequestsInfo',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_ts', models.BigIntegerField(null=True)),
                ('url', models.CharField(max_length=500)),
                ('last_date', models.CharField(max_length=50)),
                ('min_date_parameter', models.CharField(max_length=20)),
                ('max_date_parameter', models.CharField(max_length=20)),
                ('building_id', models.CharField(max_length=100)),
                ('active', models.CharField(max_length=10)),
                ('time_type', models.CharField(max_length=50)),
                ('date_pattern', models.CharField(max_length=100)),
                ('subscription_id', models.CharField(max_length=200)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='meter',
            name='canonical_building',
            field=models.ManyToManyField(related_name='meters', null=True, to='seed.CanonicalBuilding', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='meter',
            name='custom_meter_id',
            field=models.CharField(max_length=100, blank=True),
            preserve_default=True,
        ),
    ]
