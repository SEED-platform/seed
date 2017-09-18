"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author

settings for travis (travis-ci.org)
"""
from __future__ import absolute_import

import sys

from config.settings.test import *  # noqa


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'seeddb',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

if 'test' in sys.argv:
    class DisableMigrations(object):
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return "notmigrations"

    MIGRATION_MODULES = DisableMigrations()

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.cache.RedisCache',
        'LOCATION': "127.0.0.1:6379",
        'OPTIONS': {'DB': 1},
        'TIMEOUT': 300
    }
}
