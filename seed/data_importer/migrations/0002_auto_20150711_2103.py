# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('organizations', '__first__'),
        ('contenttypes', '0001_initial'),
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.AddField(
            model_name='importrecord',
            name='last_modified_by',
            field=models.ForeignKey(related_name='modified_import_records', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importrecord',
            name='organization',
            field=models.ManyToManyField(to='organizations.Organization', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importrecord',
            name='owner',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importrecord',
            name='super_organization',
            field=models.ForeignKey(related_name='import_records', blank=True, to='orgs.Organization', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='importfile',
            name='import_record',
            field=models.ForeignKey(to='data_importer.ImportRecord'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='datacoercionmapping',
            name='table_column_mapping',
            field=models.ForeignKey(to='data_importer.TableColumnMapping'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingimportrecord',
            name='building_model_content_type',
            field=models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='buildingimportrecord',
            name='import_record',
            field=models.ForeignKey(to='data_importer.ImportRecord'),
            preserve_default=True,
        ),
    ]
