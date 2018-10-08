# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('audit_logs', '0002_auditlog_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action_response',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}, help_text=b'HTTP response from action'),
            preserve_default=True,
        ),
    ]
