"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:author nicholas.long@nrel.gov
:description File contains settings needed to run SEED with docker
"""

# use importlib module to find the local_untracked file rather than a hard-coded path
import importlib
import os
import sys

from celery.utils import LOG_LEVELS
from kombu import Exchange, Queue

from config.settings.common import *  # noqa: F403


def env_var(key, default=None):
    return os.environ.get(key, default)


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
        raise Exception(f'{loc} Not defined as env variables')

DEBUG = True
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
compress = False
COMPRESS_ENABLED = compress
COMPRESS_OFFLINE = compress

ALLOWED_HOSTS = ['*']

# LBNL's BETTER tool host
# BETTER_HOST = env_var('BETTER_HOST', 'https://better.lbl.gov')
BETTER_HOST = env_var('BETTER_HOST', 'https://better-lbnl-staging.herokuapp.com')
# BETTER_HOST = env_var('BETTER_HOST', 'https://better-lbnl-development.herokuapp.com')

# Audit Template Production Host
AUDIT_TEMPLATE_HOST = env_var('AUDIT_TEMPLATE_HOST', 'https://api.labworks.org')

# PostgreSQL DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': env_var('POSTGRES_DB'),
        'USER': env_var('POSTGRES_USER'),
        'PASSWORD': env_var('POSTGRES_PASSWORD'),
        'HOST': 'db-postgres',
        'PORT': env_var('POSTGRES_PORT'),
    }
}

if SEED_TESTING:
    CELERY_BROKER_BACKEND = 'memory'
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    # this celery log level is currently not overridden.
    CELERY_LOG_LEVEL = LOG_LEVELS['WARNING']

    TESTING_MAPQUEST_API_KEY = env_var('TESTING_MAPQUEST_API_KEY', '<your_key_here>')
else:
    # Redis / Celery config
    if 'REDIS_PASSWORD' in os.environ:
        CELERY_BROKER_URL = f"redis://:{env_var('REDIS_PASSWORD')}@{env_var('REDIS_HOST', 'db-redis')}:6379/1"
    else:
        CELERY_BROKER_URL = f"redis://{env_var('REDIS_HOST', 'db-redis')}:6379/1"

    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': CELERY_BROKER_URL,
        }
    }

    CELERY_RESULT_BACKEND = CELERY_BROKER_URL

CELERY_TASK_DEFAULT_QUEUE = 'seed-docker'
# note - Queue and Exchange objects are imported in common.py
CELERY_TASK_QUEUES = (Queue(CELERY_TASK_DEFAULT_QUEUE, Exchange(CELERY_TASK_DEFAULT_QUEUE), routing_key=CELERY_TASK_DEFAULT_QUEUE),)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'level': 'ERROR', 'class': 'logging.StreamHandler'}},
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
    },
}


local_untracked_spec = importlib.util.find_spec('config.settings.local_untracked')
if local_untracked_spec is None:
    print('Unable to find the local_untracked in config/settings/local_untracked.py; Continuing with base settings...')
else:
    from config.settings.local_untracked import *  # noqa: F403

# salesforce testing
if 'SF_INSTANCE' not in vars():
    # use env vars
    SF_INSTANCE = env_var('SF_INSTANCE', '')
    SF_USERNAME = env_var('SF_USERNAME', '')
    SF_PASSWORD = env_var('SF_PASSWORD', '')
    SF_DOMAIN = env_var('SF_DOMAIN', '')
    SF_SECURITY_TOKEN = env_var('SF_SECURITY_TOKEN', '')
