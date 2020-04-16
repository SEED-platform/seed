# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django.contrib.postgres.fields.jsonb


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('orgs', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='SEEDUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.EmailField(help_text="User's email address.  Used for auth as well.", unique=True, max_length=75, verbose_name='username (email)')),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=75, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('default_custom_columns', django.contrib.postgres.fields.jsonb.JSONField(default={}, null=True, blank=True)),
                ('show_shared_buildings', models.BooleanField(default=False, help_text='shows shared buildings within search results', verbose_name='active')),
                ('api_key', models.CharField(default=b'', max_length=128, verbose_name='api key', db_index=True, blank=True)),
                ('default_organization', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='default_users', blank=True, to='orgs.Organization', null=True)),
                ('groups', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            bases=(models.Model,),
        ),
    ]
