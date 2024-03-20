"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

seed local_untracked.py

    For this to work with dev settings:
        - run with dev settings:
            $ export DJANGO_SETTINGS_MODULE=config.settings.dev
            or
            $ ./manage.py runserver --settings=config.settings.dev
        - add your settings. Make sure to update the DATABASES, AWS related configurations, and
            CACHES (i.e., everything here starting with 'your-')
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
# with AWS ElastiCache redis, the CELERY_BROKER_URL setting looks something like:
# 'rediss://:password@xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379/1?ssl_cert_reqs=required'

EAGER = os.environ.get('CELERY_ALWAYS_EAGER', 'True') == 'True'
if EAGER:
    CELERY_BROKER_BACKEND = 'memory'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
else:
    print('Using redis database')
    CELERY_BROKER_URL = 'redis://localhost:6379/1'
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': CELERY_BROKER_URL,
        }
    }
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    CELERY_TASK_DEFAULT_QUEUE = 'seed-local'
    CELERY_TASK_QUEUES = (
        Queue(
            CELERY_TASK_DEFAULT_QUEUE,
            Exchange(CELERY_TASK_DEFAULT_QUEUE),
            routing_key=CELERY_TASK_DEFAULT_QUEUE
        ),
    )
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = False


INTERNAL_IPS = ('127.0.0.1',)
