from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.models import (
    Analysis,
    AnalysisPropertyView,
    AnalysisTypes
)


class AnalysisMessage(models.Model):

    analysis_id = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    analysis_property_view_id = models.ForeignKey(AnalysisPropertyView, on_delete=models.CASCADE)
    type = models.IntegerField(choices=AnalysisTypes.MESSAGES)
    user_message = models.CharField(max_length=255, blank=False, default=None)
    debug_message = models.CharField(max_length=255, blank=False, default=None)
