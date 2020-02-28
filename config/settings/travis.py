"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

settings for travis (travis-ci.org)
"""
from __future__ import absolute_import

from config.settings.test import *  # noqa

# Travis uses a passwordless database
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'seeddb',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5433',
    }
}

TESTING_MAPQUEST_API_KEY = os.environ.get("TESTING_MAPQUEST_API_KEY")

# Setup the logging specific to Travis
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler'
        },
        'console-debug': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'runserver.log',
        },
        'celery': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'celery.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG'),
        },
        'django.db.backends': {
            'level': 'INFO',
            'handlers': ['file']
        },
        'celery': {
            'handlers': ['celery'],
            'level': 'DEBUG',
        }
    },
}
