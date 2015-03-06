"""
:copyright: (c) 2014 Building Energy Inc

"""
from BE.settings.common import *  # noqa
import os
import sys

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
            'LOCATION': "127.0.0.1:6379",
            'OPTIONS': {'DB': 1},
            'TIMEOUT': 300
        }
    }
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'verbose': {
                'format': "%(levelname)s %(asctime)s %(name)s:%(lineno)d - %(message)s"
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
                },
            'tmpfile': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'formatter': 'verbose',
                'filename': '/tmp/seed-dev.log'
            },
        },
        'loggers': {
            'django': {
                'level': 'INFO',
                'handlers': ['console', 'tmpfile'],
                },
            'seed': {
                'level': 'DEBUG',
                'handlers': ['console']
            }
        }
    }
# redis celery/message broker config
from kombu import Exchange, Queue
import djcelery
# BROKER_URL with AWS ElastiCache redis looks something like:
# 'redis://xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'
BROKER_URL = 'redis://127.0.0.1:6379/1'
BROKER_HOST = '127.0.0.1'
CELERY_DEFAULT_QUEUE = 'seed-dev'
CELERY_QUEUES = (
    Queue(
        CELERY_DEFAULT_QUEUE,
        Exchange(CELERY_DEFAULT_QUEUE),
        routing_key=CELERY_DEFAULT_QUEUE
    ),
)
djcelery.setup_loader()

try:
    INSTALLED_APPS += (
        'lettuce.django',
        'salad',
    )
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

LETTUCE_SERVER_PORT = 7001
REQUIRE_UNIQUE_EMAIL = False
LETTUCE_AVOID_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.markup',
    'django.contrib.humanize',
    'django.contrib.admin',
    'analytical',
    'ajaxuploader',
    'compress',
    'djcelery',
    'debug_toolbar',
    'django_nose',
    # 'raven.contrib.django',
    'south',
    'salad',
    'django_extensions',
    'organizations',
    'data_importer',
)

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
    import BE.settings
    local_untracked_exists = imp.find_module(
        'local_untracked', BE.settings.__path__
    )
except:
    pass

if 'local_untracked_exists' in locals():
    from BE.settings.local_untracked import *  # noqa
else:
    print >>sys.stderr, "Unable to find the local_untracked module in BE/setti\
        ngs/local_untracked.py"

# Set data directory here
SEED_DATADIR = os.path.join(SITE_ROOT, 'seed', 'data')