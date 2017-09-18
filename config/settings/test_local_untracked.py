"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
:license: see LICENSE for more details.

seed local_untracked.py

    For this to work with dev settings:
        - run with dev settings (add this line to the .bashrc):
            $ export DJANGO_SETTINGS_MODULE=config.settings.dev
            or
            $ ./manage.py runserver --settings=config.settings.dev
        - add your setting to the DATABASES, AWS S3 config,
            CACHES, and CELERY_BROKER_URL
            i.e. everything here starting with 'your-'
    For local dev, all these services can run locally on localhost or 127.0.0.1 except for S3.
"""
import os

DEBUG = True

# postgres DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seed',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# redis cache config
# with AWS ElastiCache redis, the LOCATION setting looks something like:
# 'xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379'
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "localhost:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/1'

INTERNAL_IPS = ('127.0.0.1',)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler'
        },
        'console-debug': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
        'django.db.backends': {
            'level': 'INFO',
            'handlers': ['console-debug']
        },
    },
}
