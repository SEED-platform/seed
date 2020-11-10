
from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.models import (
    Analysis,
    Cycle,
    Property,
    PropertyState
)


class AnalysisRun(models.Model):

    # For summarizing multiple AnalysisRun statuses, order matters for enums
    CREATING = 10
    READY = 20
    QUEUED = 30
    RUNNING = 40
    FAILED = 50
    STOPPED = 60
    COMPLETED = 70

    RUN_STATUSES = (
        (CREATING, 'Creating'),
        (READY, 'Ready'),
        (QUEUED, 'Queued'),
        (RUNNING, 'Running'),
        (FAILED, 'Failed'),
        (STOPPED, 'Stopped'),
        (COMPLETED, 'Completed'),
    )

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    property_state = models.OneToOneField(PropertyState, on_delete=models.CASCADE)
    output_json = JSONField(default=dict, blank=True)
    status = models.IntegerField(choices=RUN_STATUSES)
