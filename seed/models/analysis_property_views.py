# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.models import (
    Analysis,
    Cycle,
    Property,
    PropertyState
)


class AnalysisPropertyView(models.Model):
    """
    The AnalysisPropertyView provides a "snapshot" of a property at the time an
    analysis was run.
    """
    analysis = models.ForeignKey(Analysis, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE)
    # It's assumed that the linked PropertyState is never modified, thus it's
    # important to "clone" PropertyState models rather than directly using those
    # referenced by normal PropertyViews.
    property_state = models.OneToOneField(PropertyState, on_delete=models.CASCADE)
    # parsed_results can contain any results gathered from the resulting file(s)
    # that are applicable to this specific property.
    # For results not specific to the property, use the Analysis's parsed_results
    parsed_results = JSONField(default=dict, blank=True)
