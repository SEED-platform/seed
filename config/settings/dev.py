"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from __future__ import absolute_import

# use importlib module to find the local_untracked file rather than a hard-coded path
import importlib
import os

from config.settings.common import *  # noqa

DEBUG = True
compress = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

COMPRESS_ENABLED = compress
COMPRESS_OFFLINE = compress

# When running in dev mode and without nginx, specify the location of the media files.
MEDIA_URL = '/media/'

# override this in local_untracked.py
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'seed',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': '127.0.0.1',
        'PORT': '',
    },
}

MIDDLEWARE = ('seed.utils.nocache.DisableClientSideCachingMiddleware',) + MIDDLEWARE # noqa F405

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'plain': {
            'format': '%(message)s'
        },
        'file_line_number': {
            'format': "%(pathname)s:%(lineno)d - %(message)s"
        }
    },
    'filters': {
        'mute_markdown_import': {
            '()': 'seed.utils.generic.MarkdownPackageDebugFilter'
        }
    },
    # set up some log message handlers to choose from
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'file_line_number',
            'filters': ['mute_markdown_import']
        }
    },
    'loggers': {
        # the name of the logger, if empty, then this is the default logger
        '': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    },
}

REQUIRE_UNIQUE_EMAIL = False

# LBNL's BETTER tool host
BETTER_HOST = os.environ.get('BETTER_HOST', 'https://better-lbnl-development.herokuapp.com')

# Audit Template Production Host
AUDIT_TEMPLATE_HOST = os.environ.get('AUDIT_TEMPLATE_HOST', 'https://api.labworks.org')

ALLOWED_HOSTS = ['*']


local_untracked_spec = importlib.util.find_spec('config.settings.local_untracked')
if local_untracked_spec is None:
    raise Exception("Unable to find the local_untracked in config/settings/local_untracked.py")
else:
    from config.settings.local_untracked import *  # noqa
