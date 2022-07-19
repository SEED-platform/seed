# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from __future__ import absolute_import

import os

import celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = celery.Celery('seed')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.SEED_CORE_APPS + ('seed.analysis_pipelines',))

if __name__ == '__main__':
    app.start()
