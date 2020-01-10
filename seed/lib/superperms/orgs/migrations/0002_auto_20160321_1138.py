# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orgs', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='OrganizationUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', models.CharField(default=b'pending', max_length=12, choices=[(b'pending', b'Pending'), (b'accepted', b'Accepted'), (b'rejected', b'Rejected')])),
                ('role_level', models.IntegerField(default=20, choices=[(0, b'Viewer'), (10, b'Member'), (20, b'Owner')])),
                ('organization', models.ForeignKey(on_delete=models.deletion.CASCADE, to='orgs.Organization')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['organization', '-role_level'],
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='organization',
            name='users',
            field=models.ManyToManyField(related_name='orgs', through='orgs.OrganizationUser', to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
    ]
