"""
:copyright (c) 2014 - 2015, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import
from config.settings.common import *  # noqa
from kombu import Exchange, Queue

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SESSION_COOKIE_SECURE = False

# AWS credentials for S3.  Set them in environment or local_untracked.py
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
AWS_UPLOAD_CLIENT_KEY = AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
AWS_UPLOAD_CLIENT_SECRET_KEY = AWS_SECRET_ACCESS_KEY
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "be-dev-uploads")
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME

POSTGRES_CONFIG_NAMES = ['POSTGRES_PORT_5432_TCP_ADDR', 'POSTGRES_PORT_5432_TCP_PORT',
                         'POSTGRES_DATABASE_NAME', 'POSTGRES_DATABASE_USER', 'POSTGRES_ENV_POSTGRES_PASSWORD']

for loc in POSTGRES_CONFIG_NAMES:
    locals()[loc] = os.environ.get(loc)

for loc in POSTGRES_CONFIG_NAMES:
    if not locals().get(loc):
        raise Exception("%s Not defined as env variables" % loc)

REDIS_CONFIG_NAMES = ['REDIS_PORT_6379_TCP_ADDR', 'REDIS_PORT_6379_TCP_PORT']

for loc in REDIS_CONFIG_NAMES:
    locals()[loc] = os.environ.get(loc)


# override this in local_untracked.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': POSTGRES_DATABASE_NAME,
        'USER': POSTGRES_DATABASE_USER,
        'PASSWORD': POSTGRES_ENV_POSTGRES_PASSWORD,
        'HOST': POSTGRES_PORT_5432_TCP_ADDR,
        'PORT': POSTGRES_PORT_5432_TCP_PORT
    },
}

if "test" in sys.argv or "harvest" in sys.argv:
    CACHES = {
        'default': {
            'KEY_PREFIX': 'test',
            'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
            'LOCATION': '/tmp/test-cache'
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'redis_cache.cache.RedisCache',
            'LOCATION': "%s:%s" % (REDIS_PORT_6379_TCP_ADDR, REDIS_PORT_6379_TCP_PORT),
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        # set up some log message handers to chose from
        'handlers': {
            'sentry': {
                'level': 'ERROR',
                'class': 'raven.contrib.django.handlers.SentryHandler',
            },
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler'
            }
        },
        'loggers': {
            # the name of the logger, if empty, then this is the default logger
            '': {
                'level': 'INFO',
                'handlers': ['console'],
            },
            # sentry.errors are any error messages associated with failed
            # connections to sentry
            'sentry.errors': {
                'level': 'DEBUG',
                'handlers': ['console'],
                'propagate': False,
            },
        },
    }

# BROKER_URL with AWS ElastiCache redis looks something like:
# 'redis://xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'
BROKER_URL = "redis://%s:%s/1" % (REDIS_PORT_6379_TCP_ADDR, REDIS_PORT_6379_TCP_PORT)
CELERY_DEFAULT_QUEUE = 'seed-dev'
CELERY_QUEUES = (
    Queue(
        CELERY_DEFAULT_QUEUE,
        Exchange(CELERY_DEFAULT_QUEUE),
        routing_key=CELERY_DEFAULT_QUEUE
    ),
)

try:
    INSTALLED_APPS += ()
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_PLUGINS = [
        'nose_exclude.NoseExclude',
    ]
    NOSE_ARGS = ['--exclude-dir=data_importer']

except:
    if "collectstatic" not in sys.argv:
        print "Unable to import salad or lettuce."
    pass

if "test" in sys.argv:
    BROKER_BACKEND = 'memory'
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    SOUTH_TESTS_MIGRATE = True

REQUIRE_UNIQUE_EMAIL = False

INTERNAL_IPS = ('127.0.0.1',)

COMPRESS_ENABLED = False
if "COMPRESS_ENABLED" not in locals() or not COMPRESS_ENABLED:
    COMPRESS_PRECOMPILERS = ()
    COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter']
    COMPRESS_JS_FILTERS = []

ALLOWED_HOSTS = ['*']

# use imp module to find the local_untracked file rather than a hard-coded path
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
