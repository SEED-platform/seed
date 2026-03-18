"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md

:description Docker-based test settings with parallel-safe database cloning
"""

from config.settings.docker_dev import *  # noqa: F403

SEED_TESTING = True

CELERY_BROKER_BACKEND = "memory"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_LOG_LEVEL = LOG_LEVELS["WARNING"]

TESTING_MAPQUEST_API_KEY = env_var("TESTING_MAPQUEST_API_KEY", "<your_key_here>")

DATABASES["default"]["ENGINE"] = "seed.backends.postgis_parallel_tests"
DATABASES["default"]["CONN_MAX_AGE"] = 0

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "seed-docker-tests",
    }
}
