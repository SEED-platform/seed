# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.jsonb
import django_extensions.db.fields
import autoslug.fields
import django.utils.timezone
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='PermitData',
            fields=[
                # For the primary key ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                # ('name', models.CharField or models.IntegerField (blank=True or blank =False, maxLength=___, or default=___)),
                # Use DJANGO Models. documentation to get correct headers/types
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]