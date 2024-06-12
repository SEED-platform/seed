"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import celery 

def get_celery_worker_count():
    app = celery.Celery("seed")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    inspector = app.control.inspect()
    stats = inspector.stats()
    if not stats:
        return 1

    total_workers = 0
    for worker, info in stats.items():
        total_workers += info["pool"]["max-concurrency"]

    return total_workers
