"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import

import os
from os.path import abspath, join, dirname

from kombu import Exchange, Queue
from kombu.serialization import register

from seed.serializers.celery import CeleryDatetimeSerializer

SITE_ROOT = abspath(join(dirname(__file__), "..", ".."))

SESSION_COOKIE_DOMAIN = None
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

TIME_ZONE = 'America/Los_Angeles'
# TIME_ZONE = 'UTC'
USE_TZ = True
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'ns=nb-w)#2ue-mtu!s&2krzfee1-t)^z7y8gyrp6mx^d*weifh'
)

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(SITE_ROOT, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.debug',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'config.template_context.session_key',
                'config.template_context.sentry_js',
            ],
        },
    },
]

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'seed.utils.api.APIBypassCSRFMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'config.urls'

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

    'compressor',
    'django_extensions',
    'raven.contrib.django.raven_compat',
    'tos',
    'rest_framework',
    'rest_framework_swagger',
)

SEED_CORE_APPS = (
    'config',
    'seed.public',
    'seed.data_importer',
    'seed',
    'seed.lib.superperms.orgs',
    'seed.audit_logs',
    'seed.cleansing',
    'seed.functional'  # why is this a core_app?
)

# Apps with tables created by migrations, but which 3rd-party apps depend on.
# Internal apps can resolve this via South's depends_on.
HIGH_DEPENDENCY_APPS = ('seed.landing',)  # 'landing' contains SEEDUser

INSTALLED_APPS = HIGH_DEPENDENCY_APPS + INSTALLED_APPS + SEED_CORE_APPS

# apps to auto load name spaced URLs for JS use (see seed.main.views.home)
SEED_URL_APPS = (
    # 'accounts',
    'seed',
    'audit_logs',
)

MEDIA_ROOT = join(SITE_ROOT, 'collected_static')
MEDIA_URL = '/media/'

STATIC_ROOT = 'collected_static'
STATIC_URL = '/static/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

COMPRESS_ROOT = join(SITE_ROOT, 'collected_static')
COMPRESS_URL = '/static/'
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)
AWS_QUERYSTRING_AUTH = False

# django-longer-username-and-email
REQUIRE_UNIQUE_EMAIL = False

# Create a log directory if it doesn't exist. This is not used in production, but is used in dev and test
if not os.path.exists('log'):
    os.makedirs('log')

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
        }
    }
}

LOGIN_REDIRECT_URL = "/app/"

APPEND_SLASH = True

PASSWORD_RESET_EMAIL = 'reset@seedplatform.org'
SERVER_EMAIL = 'no-reply@seedplatform.org'

CELERYD_MAX_TASKS_PER_CHILD = 1

# Default queue
CELERY_DEFAULT_QUEUE = 'seed-common'
CELERY_QUEUES = (
    Queue(
        CELERY_DEFAULT_QUEUE,
        Exchange(CELERY_DEFAULT_QUEUE),
        routing_key=CELERY_DEFAULT_QUEUE
    ),
)

# Register our custom JSON serializer so we can serialize datetime objects in celery.
register('seed_json', CeleryDatetimeSerializer.seed_dumps,
         CeleryDatetimeSerializer.seed_loads,
         content_type='application/json', content_encoding='utf-8')

CELERY_ACCEPT_CONTENT = ['seed_json']
CELERY_TASK_SERIALIZER = 'seed_json'
CELERY_RESULT_SERIALIZER = 'seed_json'
CELERY_TASK_RESULT_EXPIRES = 18000  # 5 hours
CELERY_MESSAGE_COMPRESSION = 'gzip'

BROKER_URL = 'amqp://guest:guest@localhost:5672//'

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
             '--exclude-dir=seed/common']

# Matching Settings
MATCH_MIN_THRESHOLD = 0.3
MATCH_MED_THRESHOLD = 0.4

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'seed.validators.PasswordUppercaseCharacterValidator',
        'OPTIONS': {
            'quantity': 1,
        }
    },
    {
        'NAME': 'seed.validators.PasswordLowercaseCharacterValidator',
        'OPTIONS': {
            'quantity': 1,
        }
    },
    {
        'NAME': 'seed.validators.PasswordDigitValidator',
        'OPTIONS': {
            'quantity': 1,
        }
    },
]

# Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'seed.authentication.SEEDAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}

SWAGGER_SETTINGS = {
    "exclude_namespaces": ["app"],  # List URL namespaces to ignore
}
