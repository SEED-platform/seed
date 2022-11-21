"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from __future__ import absolute_import

# use importlib module to find the local_untracked file rather than a hard-coded path
import importlib
import logging
import os

from celery.utils import LOG_LEVELS

from config.settings.common import *  # noqa

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DEBUG = True
SESSION_COOKIE_SECURE = False

# override this in local_untracked.py
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'seed',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': "127.0.0.1",
        'PORT': '',
    },
}

# These celery variables can be overridden by the local_untracked values
CELERY_BROKER_BACKEND = 'memory'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# this celery log level is currently not overridden.
CELERY_LOG_LEVEL = LOG_LEVELS['WARNING']

REQUIRE_UNIQUE_EMAIL = False

INTERNAL_IPS = ('127.0.0.1',)

COMPRESS_ENABLED = False
if "COMPRESS_ENABLED" not in locals() or not COMPRESS_ENABLED:
    COMPRESS_PRECOMPILERS = ()
    COMPRESS_FILTERS = {'css': ['compressor.filters.css_default.CssAbsoluteFilter']}

ALLOWED_HOSTS = ['*']

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        # the name of the logger, if empty, then this is the default logger
        '': {
            'level': os.getenv('DJANGO_LOG_LEVEL', 'ERROR'),
            'handlers': ['console', 'file'],
        }
    },
}


local_untracked_spec = importlib.util.find_spec('config.settings.local_untracked')
if local_untracked_spec is None:
    raise Exception("Unable to find the local_untracked in config/settings/local_untracked.py")
else:
    from config.settings.local_untracked import *  # noqa


# suppress some logging on faker -- only show warnings or greater
logging.getLogger('faker.factory').setLevel(logging.ERROR)
logging.disable(logging.WARNING)
