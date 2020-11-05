
from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.landing.models import SEEDUser as User


class Analysis(models.Model):

    BSYNCR = 1

    ANALYSIS_TYPES = (
        (BSYNCR, 'BSyncr'),
    )

    name = models.CharField(max_length=255, blank=False, default=None)
    type = models.IntegerField(choices=ANALYSIS_TYPES)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    configuration = JSONField(default=dict, blank=True)
