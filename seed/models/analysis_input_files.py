# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
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
