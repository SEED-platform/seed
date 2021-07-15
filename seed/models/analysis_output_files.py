# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.db import models

from seed.models import AnalysisPropertyView


class AnalysisOutputFile(models.Model):
    """
    The AnalysisOutputFile is a file returned as output from an analysis.
    """
    BUILDINGSYNC = 1
    HTML = 2
    IMAGE_PNG = 100

    CONTENT_TYPES = (
        (BUILDINGSYNC, 'BuildingSync'),
        (HTML, 'html'),
        (IMAGE_PNG, 'PNG'),
    )

    file = models.FileField(upload_to="analysis_output_files", max_length=500)
    content_type = models.IntegerField(choices=CONTENT_TYPES)

    # An output file can be linked to one or more properties
    # Case 1: an output file is relevant to only one property
    #   e.g. the analysis returns a file containing property-specific coefficients
    #
    #   output+--->property_1
    #
    # Case 2: an output file is relevant to multiple properties
    #   e.g. the analysis returns a file of aggregated values for all properties
    #
    #         +--->property_1
    #         |
    #   output+--->property_2
    #         |
    #         +--->property_3
    analysis_property_views = models.ManyToManyField(AnalysisPropertyView)
