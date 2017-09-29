"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

# main.py does not include settings for AWS. If you want to use AWS settings then look at the
# aws.py settings file.
#
# Using this configuration expects nginx (or something similar) to server the static / media assets
#
from __future__ import absolute_import
from config.settings.common import *  # noqa
from kombu import Exchange, Queue

DEBUG = False
COMPRESS_ENABLED = True
# Need to test with cloudflare
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

ALLOWED_HOSTS = ['*']


# Enable this if not using Cloudflare
#ONLY_HTTPS = os.environ.get('ONLY_HTTPS', 'True') == 'True'
#if ONLY_HTTPS:
#    MIDDLEWARE_CLASSES = ('sslify.middleware.SSLifyMiddleware',) + \
#        MIDDLEWARE_CLASSES

# PostgreSQL DB config - override in local_untracked if needed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seed',
        'USER': 'your-username',
        'PASSWORD': 'your-password',
        'HOST': 'your-host',
        'PORT': 'your-port',
    }
}

# Redis / Celery config - override in local_untracked if needed
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "db-redis:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}
CELERY_BROKER_TRANSPORT = 'redis'
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_DEFAULT_QUEUE = 'seed-prod'
CELERY_TASK_QUEUES = (
    Queue(
        CELERY_TASK_DEFAULT_QUEUE,
        Exchange(CELERY_TASK_DEFAULT_QUEUE),
        routing_key=CELERY_TASK_DEFAULT_QUEUE
    ),
)

# logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry']
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}

try:
    from config.settings.local_untracked import *  # noqa
except ImportError:
    pass
