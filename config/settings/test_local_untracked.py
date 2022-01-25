"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
:license: see LICENSE for more details.

seed local_untracked.py

    For this to work with dev settings:
        - run with dev settings:
            $ export DJANGO_SETTINGS_MODULE=config.settings.dev
            or
            $ ./manage.py runserver --settings=config.settings.dev
        - add your settings. Make sure to update the DATABASES, AWS related configurations, and
            CACHES (i.e. everything here starting with 'your-')
    For local dev, all these services can run locally on localhost, 127.0.0.1, or 0.0.0.0.
"""
import os
from kombu import Exchange, Queue

DEBUG = True

# postgres DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'seeddb',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# redis cache config
# with AWS ElastiCache redis, the LOCATION setting looks something like:
# 'xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379'

EAGER = os.environ.get('CELERY_ALWAYS_EAGER', 'True') == 'True'
if EAGER:
    CELERY_BROKER_BACKEND = 'memory'
    CELERY_TASK_ALWAYS_EAGER = True
    task_eager_propagates = True
else:
    print("Using redis database")
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "localhost:6379",
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    broker_url = 'redis://%s/%s' % (
        CACHES['default']['LOCATION'], CACHES['default']['OPTIONS']['DB']
    )
    CELERY_RESULT_BACKEND = broker_url
    task_default_queue = 'seed-local'
    task_queues = (
        Queue(
            task_default_queue,
            Exchange(task_default_queue),
            routing_key=task_default_queue
        ),
    )
    CELERY_TASK_ALWAYS_EAGER = False
    task_eager_propagates = False


INTERNAL_IPS = ('127.0.0.1',)
