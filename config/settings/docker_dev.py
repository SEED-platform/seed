"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov

File contains settings needed to run SEED with docker
"""
from __future__ import absolute_import

from config.settings.common import *  # noqa

# Gather all the settings from the docker environment variables
ENV_VARS = ['POSTGRES_DB', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD']

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

# use imp module to find the local_untracked file rather than a hard-coded path
try:
    import imp
    import config.settings

    local_untracked_exists = imp.find_module(
        'local_untracked', config.settings.__path__
    )
except BaseException:
    pass

if 'local_untracked_exists' in locals():
    from config.settings.local_untracked import *  # noqa
else:
    print("Unable to find the local_untracked in config/settings/local_untracked.py; Continuing with base settings...")
