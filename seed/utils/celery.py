"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

import celery


def get_celery_worker_count():
    total_workers = 1
    try:
        app = celery.Celery("seed")
        app.config_from_object("django.conf:settings", namespace="CELERY")
        inspector = app.control.inspect()
        stats = inspector.stats()
        if stats:
            total_workers = sum(info["pool"]["max-concurrency"] for worker, info in stats.items()) or 1
    except Exception as e:
        logging.warning(f"An error occured while fetching celery stats: {e}")

    return total_workers
