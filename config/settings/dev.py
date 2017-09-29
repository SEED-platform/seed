"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import

import sys
from config.settings.common import *  # noqa
from kombu import Exchange, Queue
from django.conf import settings

DEBUG = True
COMPRESS_ENABLED = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# override this in local_untracked.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seed',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': "127.0.0.1",
        'PORT': '',
    },
}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "127.0.0.1:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            'format': '%(message)s'
        },
        'file_line_number': {
            'format': "%(pathname)s:%(lineno)d - %(message)s"
        }
    },
    'filters': {
        'mute_markdown_import': {
            '()': 'seed.utils.generic.MarkdownPackageDebugFilter'
        }
    },
    # set up some log message handlers to choose from
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'file_line_number',
            'filters': ['mute_markdown_import']
        }
    },
    'loggers': {
        # the name of the logger, if empty, then this is the default logger
        '': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    },
}

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_DEFAULT_QUEUE = 'seed-dev'
CELERY_QUEUES = (
    Queue(
        CELERY_TASK_DEFAULT_QUEUE,
        Exchange(CELERY_TASK_DEFAULT_QUEUE),
        routing_key=CELERY_TASK_DEFAULT_QUEUE
    ),
)

REQUIRE_UNIQUE_EMAIL = False

ALLOWED_HOSTS = ['*']

# use imp module to find the local_untracked file rather than a hard-coded path
try:
    import imp
    import config.settings

    local_untracked_exists = imp.find_module(
        'local_untracked', config.settings.__path__
    )
except:
    pass

if 'local_untracked_exists' in locals():
    from config.settings.local_untracked import *  # noqa
else:
    print >> sys.stderr, "Unable to find the local_untracked module in config/settings/local_untracked.py"
