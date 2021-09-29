"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov

File contains settings needed to run SEED with docker
"""
from __future__ import absolute_import
import os
import sys

from config.settings.common import *  # noqa

from celery.utils import LOG_LEVELS

# override MEDIA_URL (requires nginx which dev stack doesn't use)
MEDIA_URL = '/media/'

# Gather all the settings from the docker environment variables
ENV_VARS = ['POSTGRES_DB', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD']

# determine if running tests
SEED_TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

for loc in ENV_VARS:
    locals()[loc] = os.environ.get(loc)

for loc in ENV_VARS:
    if not locals().get(loc):
        raise Exception(f"{loc} Not defined as env variables")

DEBUG = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
compress = False
COMPRESS_ENABLED = compress
COMPRESS_OFFLINE = compress

ALLOWED_HOSTS = ['*']

# LBNL's BETTER tool host
BETTER_HOST = os.environ.get('BETTER_HOST', 'https://better-lbnl-development.herokuapp.com')

# PostgreSQL DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': POSTGRES_DB,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': "db-postgres",
        'PORT': POSTGRES_PORT,
    }
}

if SEED_TESTING:
    INSTALLED_APPS += (
        "django_nose",
    )
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_PLUGINS = [
        'nose_exclude.NoseExclude',
    ]
    NOSE_ARGS = [
        '--nocapture',
        # '--nologcapture',
    ]

    CELERY_BROKER_BACKEND = 'memory'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    # this celery log level is currently not overridden.
    CELERY_LOG_LEVEL = LOG_LEVELS['WARNING']

    TESTING_MAPQUEST_API_KEY = os.environ.get('TESTING_MAPQUEST_API_KEY', '<your_key_here>')
else:
    # Redis / Celery config
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "db-redis:6379",
            'OPTIONS': {
                'DB': 1
            },
            'TIMEOUT': 300,
        }
    }
    if 'REDIS_PASSWORD' in os.environ:
        CACHES['OPTIONS']['PASSWORD'] = os.environ.get('REDIS_PASSWORD')
        CELERY_BROKER_URL = 'redis://:{}@{}/{}'.format(
            CACHES['default']['OPTIONS']['PASSWORD'],
            CACHES['default']['LOCATION'],
            CACHES['default']['OPTIONS']['DB']
        )
    else:
        CELERY_BROKER_URL = 'redis://{}/{}'.format(
            CACHES['default']['LOCATION'], CACHES['default']['OPTIONS']['DB']
        )

    CELERY_BROKER_TRANSPORT = 'redis'
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL

CELERY_TASK_DEFAULT_QUEUE = 'seed-docker'
# note - Queue and Exchange objects are imported in common.py
CELERY_TASK_QUEUES = (
    Queue(
        CELERY_TASK_DEFAULT_QUEUE,
        Exchange(CELERY_TASK_DEFAULT_QUEUE),
        routing_key=CELERY_TASK_DEFAULT_QUEUE
    ),
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
    },
}

# use importlib module to find the local_untracked file rather than a hard-coded path
import importlib

local_untracked_spec = importlib.util.find_spec('config.settings.local_untracked')
if local_untracked_spec is None:
    print("Unable to find the local_untracked in config/settings/local_untracked.py; Continuing with base settings...")
else:
    from config.settings.local_untracked import *  # noqa
