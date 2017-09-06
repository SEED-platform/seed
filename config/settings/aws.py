"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import
from config.settings.common import *  # noqa
from kombu import Exchange, Queue
# import aws
from config.settings.aws import aws

# AWS settings
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
# Different names for same vars, used by django-ajax-uploader
AWS_UPLOAD_CLIENT_KEY = AWS_ACCESS_KEY_ID
AWS_UPLOAD_CLIENT_SECRET_KEY = AWS_SECRET_ACCESS_KEY
APP_NAMESPACE = "seed" + os.environ.get("STACK_NAME", "prod")
AWS_BUCKET_NAME = APP_NAMESPACE
AWS_STORAGE_BUCKET_NAME = APP_NAMESPACE
AWS_UPLOAD_BUCKET_NAME = APP_NAMESPACE

STACK_OUTPUTS = aws.get_stack_outputs()
ENV = STACK_OUTPUTS.get('StackFlavor', 'dev')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Handle SSL with django-sslify
ONLY_HTTPS = os.environ.get('ONLY_HTTPS', 'True') == 'True'
SESSION_COOKIE_SECURE = ONLY_HTTPS
CSRF_COOKIE_SECURE = ONLY_HTTPS
if ONLY_HTTPS:
    MIDDLEWARE_CLASSES = ('sslify.middleware.SSLifyMiddleware',) + \
        MIDDLEWARE_CLASSES

# Upload to S3
AWS_S3_MAX_MEMORY_SIZE = 1024 * 1024
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = DEFAULT_FILE_STORAGE
STATIC_URL = "https://%s.s3.amazonaws.com/" % AWS_STORAGE_BUCKET_NAME

# django-compressor
COMPRESS_ENABLED = True

# Celery Backend
cache_settings = aws.get_cache_endpoint()
if cache_settings is None:
    cache_settings = {
        'Address': os.environ.get('CACHE_URL', '127.0.0.1'),
        'Port': os.environ.get('CACHE_PORT', 6379)
    }
CELERY_BROKER_URL = 'redis://%(Address)s:%(Port)i/1' % cache_settings
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_DEFAULT_QUEUE = 'seed-deploy'
CELERY_TASK_QUEUES = (
    Queue(
        CELERY_TASK_DEFAULT_QUEUE,
        Exchange(CELERY_TASK_DEFAULT_QUEUE),
        routing_key=CELERY_TASK_DEFAULT_QUEUE
    ),
)

# email through SES (django-ses)
EMAIL_BACKEND = 'django_ses.SESBackend'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': "seed-deploy",
        'USER': STACK_OUTPUTS.get('DBUsername', 'postgres'),
        'PASSWORD': 'postgres',
        'HOST': STACK_OUTPUTS.get('DBAddress', '127.0.0.1'),
        'PORT': STACK_OUTPUTS.get('DBPort', ''),
    }
}
DATABASES['default']['CONN_MAX_AGE'] = None  # persistent, forever connections

# Caches (django-redis-cache)
CACHE_MIDDLEWARE_KEY_PREFIX = APP_NAMESPACE
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "%(Address)s:%(Port)s" % cache_settings,
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}

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

# django 1.5 support
ALLOWED_HOSTS = ['*']
# end django 1.5 support

try:
    from config.settings.local_untracked import *  # noqa
except ImportError:
    pass
