"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
:license: see LICENSE for more details.

seed local_untracked_docker.py

    For this to work with dev settings:
        - run with dev settings (add this line to the .bashrc):
            $ export DJANGO_SETTINGS_MODULE=config.settings.dev
            or
            $ ./manage.py runserver --settings=config.settings.dev
        - add your setting to the DATABASES, AWS S3 config,
            CACHES, and BROKER_URL
            i.e. everything here starting with 'your-'
    For local dev, all these services can run locally on localhost or 127.0.0.1 except for S3.
"""

from __future__ import absolute_import

import os
from kombu import Exchange, Queue

# Gather all the settings from the docker environment variables
ENV_VARS = ['DB_POSTGRES_PORT_5432_TCP_ADDR', 'DB_POSTGRES_PORT_5432_TCP_PORT',
            'DB_POSTGRES_ENV_POSTGRES_DB', 'DB_POSTGRES_ENV_POSTGRES_USER', 'DB_POSTGRES_ENV_POSTGRES_PASSWORD',
            'DB_REDIS_PORT_6379_TCP_ADDR', 'DB_REDIS_PORT_6379_TCP_PORT']

for loc in ENV_VARS:
    locals()[loc] = os.environ.get(loc)

for loc in ENV_VARS:
    if not locals().get(loc):
        raise Exception("%s Not defined as env variables" % loc)

# postgres DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': DB_POSTGRES_ENV_POSTGRES_DB,
        'USER': DB_POSTGRES_ENV_POSTGRES_USER,
        'PASSWORD': DB_POSTGRES_ENV_POSTGRES_PASSWORD,
        'HOST': DB_POSTGRES_PORT_5432_TCP_ADDR,
        'PORT': DB_POSTGRES_PORT_5432_TCP_PORT
    }
}

# AWS S3 config
AWS_ACCESS_KEY_ID = "your-key"
AWS_SECRET_ACCESS_KEY = "your-secret-key"
AWS_BUCKET_NAME = "your-S3-bucket"

# Different names for same vars, used by django-ajax-uploader
AWS_UPLOAD_CLIENT_KEY = AWS_ACCESS_KEY_ID
AWS_UPLOAD_CLIENT_SECRET_KEY = AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME

# choice of DEFAULT_FILE_STORAGE (s3 or filesystem)
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

STATICFILES_STORAGE = DEFAULT_FILE_STORAGE

DOMAIN_URLCONFS = {}
DOMAIN_URLCONFS['default'] = 'config.urls'

# redis cache config
# with AWS ElastiCache redis, the LOCATION setting looks something like:
# 'xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379'
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "%s:%s" % (DB_REDIS_PORT_6379_TCP_ADDR, DB_REDIS_PORT_6379_TCP_PORT),
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}

# redis celery/message broker config
BROKER_URL = "redis://%s:%s/1" % (DB_REDIS_PORT_6379_TCP_ADDR, DB_REDIS_PORT_6379_TCP_PORT)
# BROKER_URL with AWS ElastiCache redis looks something like:
# 'redis://xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'

CELERY_RESULT_BACKEND = BROKER_URL
CELERY_DEFAULT_QUEUE = 'seed-dev'
CELERY_QUEUES = (
    Queue(
        CELERY_DEFAULT_QUEUE,
        Exchange(CELERY_DEFAULT_QUEUE),
        routing_key=CELERY_DEFAULT_QUEUE
    ),
)
