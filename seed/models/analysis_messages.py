# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.db import models

from seed.models import (
    Analysis,
    AnalysisPropertyView
)


class AnalysisMessage(models.Model):
    """
    The AnalysisMessage represents user-facing messages of events that occur
    during an analysis, like a breadcrumb trail.
    """
    DEFAULT = 1

    MESSAGE_TYPES = (
        (DEFAULT, 'default'),
    )
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    # if the message is relevant to a specific property then it should be linked
    # to an AnalysisPropertyView in addition to being linked to the analysis.
    # e.g. if the AnalysisPropertyView is missing some required data
    # if the message is generic and applies to the entire analysis, analysis_property_view
    # should be None/NULL
    # e.g. the service request returned a non-200 response
    analysis_property_view = models.ForeignKey(AnalysisPropertyView, on_delete=models.CASCADE, null=True, blank=True)
    type = models.IntegerField(choices=MESSAGE_TYPES)
    # human-readable message which is presented on the frontend
    user_message = models.CharField(max_length=255, blank=False, default=None)
    # message for debugging purposes, not intended to be displayed on frontend
    debug_message = models.CharField(max_length=255, blank=True)
