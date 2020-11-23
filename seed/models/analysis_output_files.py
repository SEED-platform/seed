from django.db import models

from seed.models import (
    AnalysisPropertyView,
    AnalysisTypes
)


class AnalysisOutputFile(models.Model):

    file = models.FileField(upload_to="analysis_input_files", max_length=500)
    content_type = models.IntegerField(choices=AnalysisTypes.FILE_CONTENTS)
    analysis_property_views = models.ManyToManyField(AnalysisPropertyView)
