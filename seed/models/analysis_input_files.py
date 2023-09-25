# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import Analysis


def analysis_input_path(instance, filename):
    """Returns the path to where an AnalysisInputFile's file is stored.
    Ie only modify this function if you want to change that location.

    :param instance: AnalysisFile
    :param filename: str
    :returns: str
    """
    if instance.analysis_id is None:
        raise Exception('Unable to save analysis input file. Linked Analysis must have an ID (i.e., already saved in db)')
    return f'analysis_input_files/{instance.analysis_id}/{filename}'


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

    file = models.FileField(upload_to=analysis_input_path, max_length=500)
    content_type = models.IntegerField(choices=CONTENT_TYPES)
    analysis = models.ForeignKey(Analysis, related_name='input_files', on_delete=models.CASCADE)
