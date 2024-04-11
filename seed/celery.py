# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import os

import celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = celery.Celery("seed")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: (*settings.SEED_CORE_APPS, "seed.analysis_pipelines"))

if __name__ == "__main__":
    app.start()
