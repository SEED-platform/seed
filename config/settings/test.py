"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import

import sys

from celery.utils import LOG_LEVELS

from config.settings.common import *  # noqa

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'log/test.log'
        },
    },
    'loggers': {
        # the name of the logger, if empty, then this is the default logger
        '': {
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'handlers': ['console', 'file'],
        }
    },
}

PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

DEBUG = True
SESSION_COOKIE_SECURE = False

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

BROKER_BACKEND = 'memory'

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_LOG_LEVEL = LOG_LEVELS['DEBUG']

# Testing
INSTALLED_APPS += (
    "django_nose",
)
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_PLUGINS = [
    'nose_exclude.NoseExclude',
]
NOSE_ARGS = [
    '--nocapture',
    '--nologcapture',
]

REQUIRE_UNIQUE_EMAIL = False

INTERNAL_IPS = ('127.0.0.1',)

COMPRESS_ENABLED = False
if "COMPRESS_ENABLED" not in locals() or not COMPRESS_ENABLED:
    COMPRESS_PRECOMPILERS = ()
    COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter']
    COMPRESS_JS_FILTERS = []

ALLOWED_HOSTS = ['*']

# use imp module to find the local_untracked file rather than a hard-coded path
# TODO: There seems to be a bunch of loading of other files in these settings. First this loads the common, then this, then anything in the untracked file
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
