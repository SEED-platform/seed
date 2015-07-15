"""
:copyright: (c) 2014 Building Energy Inc
"""
import os
import sys
import logging
from os.path import abspath, join, dirname

SITE_ROOT = abspath(join(dirname(__file__), "..", ".."))

SEED_DATADIR = join(SITE_ROOT, 'seed', 'data')

SESSION_COOKIE_DOMAIN = None
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# sentry
SENTRY_DSN = os.environ.get('SENTRY_DSN', None)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS
SEND_BROKEN_LINK_EMAILS = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

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

ROOT_URLCONF = 'config.urls'

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

    'compressor',
    'django_extensions',
    'organizations',
    'raven.contrib.django',
    'south',
    'tos',
)

BE_CORE_APPS = (
    'config',
    'seed.public',
    'seed.data_importer',
    'seed',
    'seed.lib.superperms.orgs',
    'seed.audit_logs',
)

# Apps with tables created by migrations, but which 3rd-party apps depend on.
# Internal apps can resolve this via South's depends_on.
HIGH_DEPENDENCY_APPS = ('seed.landing',)  # 'landing' contains SEEDUser

INSTALLED_APPS = HIGH_DEPENDENCY_APPS + INSTALLED_APPS + BE_CORE_APPS

# apps to auto load namespaced urls for JS use (see seed.main.views.home)
BE_URL_APPS = (
    'accounts',
    'ajaxuploader',
    'data_importer',
    'seed',
    'audit_logs',
    'projects',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
    'config.template_context.compress_enabled',
    'config.template_context.session_key',
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
    'disable_existing_loggers': True,
    'formatters': {
        'plain': {
            'format': '%(message)s'
        },
        'verbose': {
            'format': "%(levelname)5.5s %(asctime)24.24s %(name).20s line \
            %(lineno)d\n%(pathname)s\n%(message)s"
        },
        'abbreviated': {
            'format': '%(name)20.20s:%(lineno)05d %(message).55s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.handlers.SentryHandler',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'abbreviated_console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'abbreviated',
        },
        'verbose_console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': ['sentry'],
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    }
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

SOUTH_TESTS_MIGRATE = False
SOUTH_MIGRATION_MODULES = {
}

BROKER_HOST = "localhost"
BROKER_PORT = 5672
BROKER_USER = "guest"
BROKER_PASSWORD = "guest"
BROKER_VHOST = "/"

LOG_FILE = join(SITE_ROOT, '../logs/py.log/')

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
NOSE_ARGS = ['--exclude-dir=libs/dal',
             '--exclude-dir=data_importer',
             '--exclude-dir=seed/common']


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
