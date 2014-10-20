"""
:copyright: (c) 2014 Building Energy Inc

settings for CircleCI (circleci.com)
"""
from BE.settings.dev import *  # noqa

# SENTRY_DSN set in circleci env

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'circle_test',
        'USER': 'ubuntu',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': ['127.0.0.1:11211', ],
        'TIMEOUT': 60,
    }
}

BROKER_HOST = "127.0.0.1"
SOUTH_TESTS_MIGRATE = True
CELERY_ALWAYS_EAGER = True

try:
    from BE.settings.local_untracked import *  # noqa
except:
    pass
