from django.db import models

from seed.models import (
    Analysis,
    AnalysisPropertyView,
    AnalysisTypes
)


class AnalysisMessage(models.Model):
    """
    The AnalysisMessage represents user-facing messages of events that occur
    during an analysis, like a breadcrumb trail.
    """
    # if the message is relevant to the entire analysis, ie not property specific,
    # then it should be linked to an analysis and not linked to an AnalysisPropertyView
    # e.g. the API for the analysis service returned a non 200 response
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    # if the message is relevant to a specific property then it should be linked
    # to an AnalysisPropertyView
    # e.g. if the AnalysisPropertyView is missing some required data
    analysis_property_view = models.ForeignKey(AnalysisPropertyView, on_delete=models.CASCADE)
    type = models.IntegerField(choices=AnalysisTypes.MESSAGES)
    # human-readable message which is presented on the frontend
    user_message = models.CharField(max_length=255, blank=False, default=None)
    # message for debugging purposes, not intended to be displayed on frontend
    debug_message = models.CharField(max_length=255, blank=False, default=None)
