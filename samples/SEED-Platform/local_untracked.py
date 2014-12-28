"""
:copyright: (c) 2014 Building Energy Inc
:license: see LICENSE for more details.

seed local_untracked.py

    For this to work with dev settings:
        - run with dev settings (add this line to the .bashrc):
            $ export DJANGO_SETTINGS_MODULE=BE.settings.dev
            or
            $ DJANGO_SETTINGS_MODULE=BE.settings.dev ./manage.py runserver
        - add your setting to the DATABASES, AWS S3 config, 
            CACHES, and BROKER_URL
            i.e. everthing here starting with 'your-'
    For local dev, all these services can run locally on localhost or 127.0.0.1
    except for S3.
"""

DEBUG=True

SERVER_EMAIL="noreply@lbl.gov"
PASSWORD_RESET_EMAIL="noreply@lbl.gov"
COMPRESS_ENABLED = False
ALLOWED_HOSTS = ['*',]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/vagrant/seed-django.log',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propogate': True
        },
    },
}

# postgres DB config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seed_dev',
        'USER': 'seeduser',
        'PASSWORD': 'testing',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# AWS S3 config
AWS_ACCESS_KEY_ID = "AKIAJB4POH67IWWXSHIQ"
AWS_SECRET_ACCESS_KEY = "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"
AWS_BUCKET_NAME = "seed-seeddev"

# Different names for same vars, used by django-ajax-uploader
AWS_UPLOAD_CLIENT_KEY = AWS_ACCESS_KEY_ID
AWS_UPLOAD_CLIENT_SECRET_KEY = AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME
# config for AWS S3 as storage backend
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = DEFAULT_FILE_STORAGE
DOMAIN_URLCONFS = {}
DOMAIN_URLCONFS['default'] = 'urls.main'

# redis cache config
# with AWS ElastiCache redis, the LOCATION setting looks something like:
# 'xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379'
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "127.0.0.1:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}

# redis celery/message broker config
from kombu import Exchange, Queue
import djcelery
# BROKER_URL with AWS ElastiCache redis looks something like:
# 'redis://xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'
BROKER_URL = 'redis://127.0.0.1:6379/1'
CELERY_DEFAULT_QUEUE = 'seed-dev'
CELERY_QUEUES = (
    Queue(
        CELERY_DEFAULT_QUEUE,
        Exchange(CELERY_DEFAULT_QUEUE),
        routing_key=CELERY_DEFAULT_QUEUE
    ),
)
djcelery.setup_loader()
