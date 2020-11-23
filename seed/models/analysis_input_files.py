from django.db import models

from seed.models import (
    Analysis,
    AnalysisTypes
)


class AnalysisInputFile(models.Model):

    file = models.FileField(upload_to="analysis_input_files", max_length=500)
    content_type = models.IntegerField(choices=AnalysisTypes.FILE_CONTENTS)
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
