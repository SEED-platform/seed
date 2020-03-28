"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import

from config.settings.common import *  # noqa
from celery.utils import LOG_LEVELS

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

# These celery variables can be overriden by the local_untracked values
CELERY_BROKER_BACKEND = 'memory'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
# this celery log level is currently not overridden.
CELERY_LOG_LEVEL = LOG_LEVELS['WARNING']

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

# use imp module to find the local_untracked file rather than a hard-coded path
try:
    import imp
    import config.settings

    local_untracked_exists = imp.find_module(
        'local_untracked', config.settings.__path__
    )
except BaseException:
    pass


if 'local_untracked_exists' in locals():
    from config.settings.local_untracked import *  # noqa
else:
    raise Exception("Unable to find the local_untracked in config/settings/local_untracked.py")

# suppress some logging -- only show warnings or greater
# logging.getLogger('faker.factory').setLevel(logging.ERROR)
# logging.disable(logging.WARNING)
