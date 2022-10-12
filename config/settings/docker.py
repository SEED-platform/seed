"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author nicholas.long@nrel.gov

File contains settings needed to run SEED with docker
"""
from __future__ import absolute_import

import os

from kombu import Exchange, Queue

from config.settings.common import *  # noqa

# Gather all the settings from the docker environment variables
ENV_VARS = ['POSTGRES_DB', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', ]

# See the django docs for more info on these env vars:
# https://docs.djangoproject.com/en/3.0/topics/email/#smtp-backend
SMTP_ENV_VARS = ['EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER',
                 'EMAIL_HOST_PASSWORD', 'EMAIL_USE_TLS', 'EMAIL_USE_SSL']

# The optional vars will set the SERVER_EMAIL information as needed
OPTIONAL_ENV_VARS = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SES_REGION_NAME',
                     'AWS_SES_REGION_ENDPOINT', 'SERVER_EMAIL', 'SENTRY_JS_DSN', 'SENTRY_RAVEN_DSN',
                     'REDIS_PASSWORD', 'DJANGO_EMAIL_BACKEND',
                     'POSTGRES_HOST'] + SMTP_ENV_VARS

for loc in ENV_VARS + OPTIONAL_ENV_VARS:
    locals()[loc] = os.environ.get(loc)

for loc in ENV_VARS:
    if not locals().get(loc):
        raise Exception("%s Not defined as env variables" % loc)

DEBUG = False
COMPRESS_ENABLED = False
# COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'
# COMPRESS_OFFLINE = True

# Make sure to disable secure cookies and csrf when using Cloudflare
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

ALLOWED_HOSTS = ['*']

# By default we are using SES as our email client. If you would like to use
# another backend (e.g., SMTP), then please update this model to support both and
# create a pull request.
EMAIL_BACKEND = os.environ.get('DJANGO_EMAIL_BACKEND', 'django_ses.SESBackend')
PASSWORD_RESET_EMAIL = SERVER_EMAIL # noqa F405
DEFAULT_FROM_EMAIL = SERVER_EMAIL  # noqa F405
POST_OFFICE = {
    'BACKENDS': {
        'default': EMAIL_BACKEND,
        'post_office_backend': EMAIL_BACKEND,
    },
    'CELERY_ENABLED': True,
}

# PostgreSQL DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': POSTGRES_DB,  # noqa F405
        'USER': POSTGRES_USER,  # noqa F405
        'PASSWORD': POSTGRES_PASSWORD,  # noqa F405
        'HOST': os.environ.get('POSTGRES_HOST', 'db-postgres'),  # noqa F405
        'PORT': POSTGRES_PORT,  # noqa F405
    }
}

# Redis / Celery config
if 'REDIS_PASSWORD' in os.environ:
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "db-redis:6379",
            'OPTIONS': {
                'DB': 1,
                'PASSWORD': REDIS_PASSWORD,  # noqa F405
            },
            'TIMEOUT': 300
        }
    }
    CELERY_BROKER_URL = 'redis://:%s@%s/%s' % (
        CACHES['default']['OPTIONS']['PASSWORD'],
        CACHES['default']['LOCATION'],
        CACHES['default']['OPTIONS']['DB']
    )
else:
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "db-redis:6379",
            'OPTIONS': {
                'DB': 1
            },
            'TIMEOUT': 300
        }
    }
    CELERY_BROKER_URL = 'redis://%s/%s' % (
        CACHES['default']['LOCATION'], CACHES['default']['OPTIONS']['DB']
    )

CELERY_BROKER_TRANSPORT = 'redis'
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

if 'default' in SECRET_KEY:  # noqa F405
    print("WARNING: SECRET_KEY is defaulted. Makes sure to override SECRET_KEY in local_untracked or env var")

if 'SENTRY_RAVEN_DSN' in os.environ:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_RAVEN_DSN'),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=0.25,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True
    )

# SENTRY_JS_DSN is directly passed through to the Sentry configuration for JS.
