"""
:copyright: (c) 2014 Building Energy Inc
"""

# Django settings
import os
import sys

import logging
from os.path import abspath, join, dirname

SITE_ROOT = abspath(join(dirname(__file__), "..", ".."))

SEED_DATADIR = join(SITE_ROOT, 'seed', 'data')

SESSION_COOKIE_DOMAIN = None
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# TODO: are we still using sentry?
# sentry
SENTRY_DSN = os.environ.get('SENTRY_DSN', None)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS
SEND_BROKEN_LINK_EMAILS = True

TIME_ZONE = 'America/Los_Angeles'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'ns=nb-w)#2ue-mtu!s&2krzfee1-t)^z7y8gyrp6mx^d*weifh'
)

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'seed.utils.api.APIBypassCSRFMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'raven.contrib.django.middleware.Sentry404CatchMiddleware',
    'pagination.middleware.PaginationMiddleware',
)

ROOT_URLCONF = 'BE.urls'

TEMPLATE_DIRS = (
    join(SITE_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.admin',
    'analytical',
    'ajaxuploader',
    'djcelery',
    'django_nose',
    'compressor',
    'django_extensions',
    'organizations',
    'superperms.orgs',
    'raven.contrib.django',
    'south',
    'tos',
    'public',
)

BE_CORE_APPS = (
    'BE',
    'data_importer',
    'seed',
    'audit_logs',
)

# Apps with tables created by migrations, but which 3rd-party apps depend on.
# Internal apps can resolve this via South's depends_on.
HIGH_DEPENDENCY_APPS = ('landing',)  # 'landing' contains SEEDUser

INSTALLED_APPS = HIGH_DEPENDENCY_APPS + INSTALLED_APPS + BE_CORE_APPS

# apps to auto load namespaced urls for JS use (see seed.main.views.home)
BE_URL_APPS = (
    'accounts',
    'ajaxuploader',
    'data_importer',
    'seed',
    'projects',
    'audit_logs',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'BE.template_context.compress_enabled',
    'BE.template_context.session_key',
)

MEDIA_ROOT = join(SITE_ROOT, 'collected_static')
MEDIA_URL = "/media/"

STATIC_ROOT = "collected_static"
STATIC_URL = '/static/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

COMPRESS_ROOT = STATIC_ROOT
COMPRESS_URL = STATIC_URL
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)
AWS_QUERYSTRING_AUTH = False

# django-longer-username-and-email
REQUIRE_UNIQUE_EMAIL = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'log/test.log',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

LOGIN_REDIRECT_URL = "/app/"

APPEND_SLASH = True

PASSWORD_RESET_EMAIL = 'reset@buildingenergy.com'
SERVER_EMAIL = 'no-reply@buildingenergy.com'


# Celery queues
from kombu import Exchange, Queue
import djcelery

djcelery.setup_loader()

CELERYD_MAX_TASKS_PER_CHILD = 1

# Default queue
CELERY_DEFAULT_QUEUE = 'be_core'
CELERY_QUEUES = (
    Queue('be_core', Exchange('be_core'), routing_key='be_core'),
)

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_VHOST = "/"

LOG_FILE = join(SITE_ROOT, '../logs/py.log/')

# DEBUG TOOLBAR
INTERNAL_IPS = ('127.0.0.1',)

# Set translation languages for i18n
LANGUAGES = (
    ('en', 'English'),
)
LOCALE_PATHS = (
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Added By Gavin on 1/27/2014
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_PLUGINS = [
    'nose_exclude.NoseExclude',
]

# Django 1.5+ way of doing user profiles
AUTH_USER_MODEL = 'landing.SEEDUser'

# Matching Settings
MATCH_MIN_THRESHOLD = 0.3
MATCH_MED_THRESHOLD = 0.4

# django-passwords settings: passwords should requre alphnumberic and 8
# character minimum, with a minimum of 1 upper and 1 lower case character
PASSWORD_MIN_LENGTH = 8
PASSWORD_COMPLEXITY = {
    "UPPER": 1,  # at least 1 Uppercase
    "LOWER": 1,  # at least 1 Lowercase
    "DIGITS": 1,  # at least 1 Digit
}

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

# redis celery/message broker config
from kombu import Exchange, Queue
import djcelery
# BROKER_URL with AWS ElastiCache redis looks something like:
# 'redis://xx-yy-zzrr0aax9a.ntmprk.0001.usw2.cache.amazonaws.com:6379/1'
# TODO: use different redis queue for testing. if you change this here, then it is overloaded later
BROKER_BACKEND = 'memory'
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
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
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
    NOSE_ARGS = [
        '--exclude-dir=data_importer',
        '--exclude-dir=seed/common',
        '--nocapture',
        '--nologcapture'
    ]

except:
    if "collectstatic" not in sys.argv:
        print "Unable to import salad or lettuce."
    pass

# You have to run south tests migration due to the BEDES migration (30-32) that adds a bunch of columns
# There are two test failures if you disable this
#   File "/Users/nlong/working/seed/seed/tests/test_views.py", line 262, in test_get_columns
#   Assertion on ?
# To make tests run faster pass the REUSE_DB=1 env var to the test command
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
    'raven.contrib.django',
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
# TODO: There seems to be a bunch of loading of other files in these settings. First this loads the common, then this, then anything in the untracked file
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
    print >> sys.stderr, "Unable to find the local_untracked module in BE/settings/local_untracked.py"
