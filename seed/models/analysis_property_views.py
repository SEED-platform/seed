from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.models import (
    Analysis,
    Cycle,
    Property,
    PropertyState
)


class AnalysisPropertyView(models.Model):

    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    property_state = models.OneToOneField(PropertyState, on_delete=models.CASCADE)
    parsed_results = JSONField(default=dict, blank=True)
