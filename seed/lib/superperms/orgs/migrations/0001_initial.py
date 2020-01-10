# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ExportableField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('field_model', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=200)),
            ],
            options={
                'ordering': ['organization', 'name'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('query_threshold', models.IntegerField(null=True, blank=True)),
                ('parent_org', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='child_orgs', blank=True, to='orgs.Organization', null=True)),
            ],
            options={
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='exportablefield',
            name='organization',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='exportable_fields', to='orgs.Organization'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='exportablefield',
            unique_together=set([('field_model', 'name', 'organization')]),
        ),
    ]
