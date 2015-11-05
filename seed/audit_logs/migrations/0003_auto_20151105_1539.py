# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_pgjson.fields


class Migration(migrations.Migration):

    dependencies = [
        ('audit_logs', '0002_auditlog_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action_response',
            field=django_pgjson.fields.JsonField(default={}, help_text=b'HTTP response from action'),
            preserve_default=True,
        ),
    ]
