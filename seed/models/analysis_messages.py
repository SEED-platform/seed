from django.db import models

from seed.models import (
    Analysis,
    AnalysisPropertyView,
    AnalysisTypes
)


class AnalysisMessage(models.Model):

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    analysis_property_view = models.ForeignKey(AnalysisPropertyView, on_delete=models.CASCADE)
    type = models.IntegerField(choices=AnalysisTypes.MESSAGES)
    user_message = models.CharField(max_length=255, blank=False, default=None)
    debug_message = models.CharField(max_length=255, blank=False, default=None)
