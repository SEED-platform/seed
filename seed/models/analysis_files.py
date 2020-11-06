
from django.db import models

from seed.models import AnalysisRun


class AnalysisFile(models.Model):

    BUILDINGSYNC = 1

    FILE_TYPES = (
        (BUILDINGSYNC, 'BuildingSync'),
    )

    file = models.FileField(upload_to="analysis_files", max_length=500)
    file_type = models.IntegerField(choices=FILE_TYPES)
    input_for_run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE, related_name='input_files', blank=True, null=True)
    output_for_run = models.ForeignKey(AnalysisRun, on_delete=models.CASCADE, related_name='output_files', blank=True, null=True)
