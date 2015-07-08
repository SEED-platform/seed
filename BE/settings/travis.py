"""

settings for travis (travis-ci.org)
"""
from BE.settings.dev import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seeddb',
        'USER': 'seeduser',
        'PASSWORD': 'seedpass',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "127.0.0.1:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}

BROKER_URL = 'redis://127.0.0.1:6379/1'

# Make sure to run the migrations on the CI machines for testing. This is also enabled when running tests locally
SOUTH_TESTS_MIGRATE = True

DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
STATICFILES_STORAGE = DEFAULT_FILE_STORAGE
DOMAIN_URLCONFS = {}
DOMAIN_URLCONFS['default'] = 'BE.urls'
