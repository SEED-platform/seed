# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django_pgjson.fields
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', django_extensions.db.fields.CreationDateTimeField(default=django.utils.timezone.now, verbose_name='created', editable=False, blank=True)),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, verbose_name='modified', editable=False, blank=True)),
                ('object_id', models.PositiveIntegerField(null=True)),
                ('audit_type', models.IntegerField(default=0, choices=[(0, b'Log'), (1, b'Note')])),
                ('action', models.CharField(help_text=b'method triggering audit', max_length=128, null=True, db_index=True, blank=True)),
                ('action_response', django_pgjson.fields.JsonField(default={}, help_text=b'HTTP response from action', null=True, blank=True)),
                ('action_note', models.TextField(help_text=b'either the note text or a description of the action', null=True, blank=True)),
                ('content_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
                ('organization', models.ForeignKey(related_name='audit_logs', to='orgs.Organization')),
            ],
            options={
                'ordering': ('-created',),
            },
            bases=(models.Model,),
        ),
    ]
