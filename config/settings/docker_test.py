"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:description Docker-based test settings with parallel-safe database cloning
"""

from config.settings.docker_dev import *  # noqa: F403

CELERY_BROKER_BACKEND = "memory"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

TESTING_MAPQUEST_API_KEY = env_var("TESTING_MAPQUEST_API_KEY", "<your_key_here>")

TIMESCALE_DB_BACKEND_BASE = "seed.backends.postgis_parallel_tests"
DATABASES["default"]["ENGINE"] = "seed.backends.timescale_postgis"
DATABASES["default"]["CONN_MAX_AGE"] = 0

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "seed-docker-tests",
    }
}

# salesforce testing
if "SF_INSTANCE" not in vars():
    # use env vars
    SF_INSTANCE = env_var("SF_INSTANCE", "")
    SF_USERNAME = env_var("SF_USERNAME", "")
    SF_PASSWORD = env_var("SF_PASSWORD", "")
    SF_DOMAIN = env_var("SF_DOMAIN", "")
    SF_SECURITY_TOKEN = env_var("SF_SECURITY_TOKEN", "")

LOGGING = {
    **LOGGING,
    "loggers": {
        **LOGGING.get("loggers", {}),
        "celery": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery.app.trace": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
