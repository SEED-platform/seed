"""
:copyright (c) 2014 - 2022, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.
:author
"""
from __future__ import absolute_import

import os

from django.utils.translation import gettext_lazy as _
from kombu.serialization import register

from seed.serializers.celery import CeleryDatetimeSerializer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROTOCOL = os.environ.get('PROTOCOL', 'https')

SESSION_COOKIE_DOMAIN = None
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
DATA_UPLOAD_MAX_MEMORY_SIZE = None

# TODO: remove managers, admins in config files.
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

TIME_ZONE = 'America/Los_Angeles'
USE_TZ = True
SITE_ID = 1

USE_I18N = True
LANGUAGES = (
    ('en', _('English')),
    ('fr-ca', _('French (Canada)')),
)
LOCALE_PATHS = ('locale',)
LANGUAGE_CODE = 'en-us'

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'default-ns=nb-w)#2ue-mtu!s&2krzfee1-t)^z7y8gyrp6mx^d*weifh'
)

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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
MIDDLEWARE = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'seed.utils.api.APIBypassCSRFMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'config.urls'

DJANGO_CORE_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    'compressor',
    'django_extensions',
    'django_filters',
    'rest_framework',
    'drf_yasg',
    'oauth2_provider',
    'oauth2_jwt_provider',
    'crispy_forms',  # needed to squash warnings around collectstatic with rest_framework
    'post_office',
    'storages'
)

SEED_CORE_APPS = (
    'config',
    'seed.public',
    'seed.data_importer',
    'seed',
    'seed.lib.superperms.orgs',
    'seed.docs'
)

# Added by Ashray Wadhwa (08/19/2020)
POST_OFFICE = {
    'BACKENDS': {
        'default': 'smtp.EmailBackend',
        'post_office_backend': 'django.core.mail.backends.console.EmailBackend',
    },
    'CELERY_ENABLED': True,
}


# Apps with tables created by migrations, but which 3rd-party apps depend on.
# Internal apps can resolve this via South's depends_on.
HIGH_DEPENDENCY_APPS = ('seed.landing',)  # 'landing' contains SEEDUser

INSTALLED_APPS = HIGH_DEPENDENCY_APPS + DJANGO_CORE_APPS + SEED_CORE_APPS

# apps to auto load name spaced URLs for JS use (see seed.urls)
SEED_URL_APPS = (
    'seed',
)

MEDIA_URL = '/api/v3/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'collected_static')
COMPRESS_AUTOPREFIXER_BINARY = 'node_modules/.bin/postcss'
COMPRESS_FILTERS = {
    'css': [
        'compressor.filters.css_default.CssAbsoluteFilter',
        'django_compressor_autoprefixer.AutoprefixerFilter',
        'compressor.filters.cssmin.CSSMinFilter',
    ]
}
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'vendors')
]
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'django_libsass.SassCompiler'),
)
AWS_QUERYSTRING_AUTH = False

USE_S3 = os.getenv('USE_S3') == 'TRUE'
if USE_S3:
    # aws settings
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
    # s3 media settings
    MEDIA_ROOT = "media"
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# django-longer-username-and-email
REQUIRE_UNIQUE_EMAIL = False

# Create a log directory if it doesn't exist.
# This is not used in production, but is used in dev and test
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
    },
    'loggers': {
        '': {
            'level': 'INFO',
            'handlers': ['console'],
        }
    }
}

LOGIN_REDIRECT_URL = "/app/"

APPEND_SLASH = True

# Register our custom JSON serializer so we can serialize datetime objects in celery.
register('seed_json', CeleryDatetimeSerializer.seed_dumps,
         CeleryDatetimeSerializer.seed_loads,
         content_type='application/json', content_encoding='utf-8')
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1
CELERY_ACCEPT_CONTENT = ['seed_json', 'pickle']
CELERY_TASK_SERIALIZER = 'seed_json'
CELERY_RESULT_SERIALIZER = 'seed_json'
CELERY_RESULT_EXPIRES = 86400  # 24 hours
CELERY_TASK_COMPRESSION = 'gzip'

# hmm, we are logging outside the context of the app?
LOG_FILE = os.path.join(BASE_DIR, '../logs/py.log/')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SERVER_EMAIL = 'info@seed-platform.org'
PASSWORD_RESET_EMAIL = SERVER_EMAIL
DEFAULT_FROM_EMAIL = SERVER_EMAIL

# Added By Gavin on 1/27/2014
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_PLUGINS = [
    'nose_exclude.NoseExclude',
]

AUTH_USER_MODEL = 'landing.SEEDUser'
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
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Django Rest Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',
        'seed.authentication.SEEDAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS':
        'seed.utils.pagination.ResultsListPagination',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'PAGE_SIZE': 25,
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DATETIME_INPUT_FORMATS': (
        '%Y:%m:%d', 'iso-8601', '%Y-%m-%d'
    ),
    'EXCEPTION_HANDLER': 'seed.exception_handler.custom_exception_handler',
}

SWAGGER_SETTINGS = {
    'TAGS_SORTER': 'alpha',
    'DEFAULT_FIELD_INSPECTORS': [
        'drf_yasg.inspectors.CamelCaseJSONFilter',
        'drf_yasg.inspectors.InlineSerializerInspector',  # this disables models and is the only non-default entry
        'drf_yasg.inspectors.RelatedFieldInspector',
        'drf_yasg.inspectors.ChoiceFieldInspector',
        'drf_yasg.inspectors.FileFieldInspector',
        'drf_yasg.inspectors.DictFieldInspector',
        'drf_yasg.inspectors.JSONFieldInspector',
        'drf_yasg.inspectors.HiddenFieldInspector',
        'drf_yasg.inspectors.RecursiveFieldInspector',
        'drf_yasg.inspectors.SerializerMethodFieldInspector',
        'drf_yasg.inspectors.SimpleFieldInspector',
        'drf_yasg.inspectors.StringDefaultFieldInspector',
    ],
    'DOC_EXPANSION': 'none',
    'LOGOUT_URL': '/accounts/logout',
}

BSYNCR_SERVER_HOST = os.environ.get('BSYNCR_SERVER_HOST')
BSYNCR_SERVER_PORT = os.environ.get('BSYNCR_SERVER_PORT', '80')

# LBNL's BETTER tool host location
BETTER_HOST = os.environ.get('BETTER_HOST', 'https://better.lbl.gov')

# Audit Template Production Host
AUDIT_TEMPLATE_HOST = os.environ.get('AUDIT_TEMPLATE_HOST', 'https://buildingenergyscore.energy.gov')

# Google reCAPTCHA env variable for self-registration. SITE_KEY defaults
# to the key registered for SEED. Override it needing to test.
# https://developers.google.com/recaptcha/docs/faq#id-like-to-run-automated-tests-with-recaptcha.-what-should-i-do
GOOGLE_RECAPTCHA_SITE_KEY = os.environ.get('GOOGLE_RECAPTCHA_SITE_KEY', '6LexR2MaAAAAAMkCFmLaucT0KwSfx0PjiX-cf6rV')
GOOGLE_RECAPTCHA_SECRET_KEY = os.environ.get('GOOGLE_RECAPTCHA_SECRET_KEY')

# Certification
# set this for a default validity_duration
# should be a integer representing a number of days
# GREEN_ASSESSMENT_DEFAULT_VALIDITY_DURATION=5 * 365
GREEN_ASSESSMENT_DEFAULT_VALIDITY_DURATION = None

# Config to include v2 APIs
INCLUDE_SEED_V2_APIS = os.environ.get('INCLUDE_SEED_V2_APIS', 'true').lower() == 'true'

# Config self registration
INCLUDE_ACCT_REG = os.environ.get('INCLUDE_ACCT_REG', 'true').lower() == 'true'
