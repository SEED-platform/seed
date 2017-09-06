"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov

File contains settings needed to run SEED with docker
"""
from __future__ import absolute_import

from config.settings.common import *  # noqa

# Gather all the settings from the docker environment variables
ENV_VARS = ['POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD', ]

for loc in ENV_VARS:
    locals()[loc] = os.environ.get(loc)

for loc in ENV_VARS:
    if not locals().get(loc):
        raise Exception("%s Not defined as env variables" % loc)

DEBUG = False
COMPRESS_ENABLED = True

ALLOWED_HOSTS = ['*']

# PostgreSQL DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': POSTGRES_DB,
        'USER': POSTGRES_USER,
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': "db-postgres",
        'PORT': 5432,
    }
}

# Redis / Celery config
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "db-redis:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}
CELERY_BROKER_TRANSPORT = 'redis'
CELERY_BROKER_URL = "redis://db-redis:6379/1"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_DEFAULT_QUEUE = 'seed-docker'
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

if 'default' in SECRET_KEY:
    print("WARNING: SECRET_KEY is defaulted. Makes sure to override SECKET_KEY in local_untracked or env var")

