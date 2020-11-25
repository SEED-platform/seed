from django.db import models

from seed.models import Analysis


class AnalysisInputFile(models.Model):
    """
    The AnalysisInputFile is a file used as input for an analysis.

    For example, if running an analysis on multiple properties, it might be a
    CSV containing data collected from each property.
    """
    BUILDINGSYNC = 1

    CONTENT_TYPES = (
        (BUILDINGSYNC, 'BuildingSync'),
    )

    file = models.FileField(upload_to="analysis_input_files", max_length=500)
    content_type = models.IntegerField(choices=CONTENT_TYPES)
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
