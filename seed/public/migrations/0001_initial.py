# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='SharedBuildingField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('field_type', models.IntegerField(default=0, choices=[(0, b'Internal'), (1, b'Public')])),
                ('field', models.ForeignKey(on_delete=models.deletion.CASCADE, to='orgs.ExportableField')),
                ('org', models.ForeignKey(on_delete=models.deletion.CASCADE, to='orgs.Organization')),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'abstract': False,
                'get_latest_by': 'modified',
            },
            bases=(models.Model,),
        ),
    ]
