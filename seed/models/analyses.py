# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.contrib.postgres.fields import JSONField
from django.db import models

from seed.landing.models import SEEDUser as User
from seed.lib.superperms.orgs.models import Organization


class Analysis(models.Model):
    """
    The Analysis represents an analysis performed on one or more properties.
    """
    BSYNCR = 1

    SERVICE_TYPES = (
        (BSYNCR, 'BSyncr'),
    )

    CREATING = 10
    READY = 20
    QUEUED = 30
    RUNNING = 40
    FAILED = 50
    STOPPED = 60
    COMPLETED = 70

    STATUS_TYPES = (
        (CREATING, 'Creating'),
        (READY, 'Ready'),
        (QUEUED, 'Queued'),
        (RUNNING, 'Running'),
        (FAILED, 'Failed'),
        (STOPPED, 'Stopped'),
        (COMPLETED, 'Completed'),
    )

    name = models.CharField(max_length=255, blank=False, default=None)
    service = models.IntegerField(choices=SERVICE_TYPES)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.IntegerField(choices=STATUS_TYPES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    configuration = JSONField(default=dict, blank=True)
    # parsed_results can contain any results gathered from the resulting file(s)
    # that are applicable to the entire analysis (ie all properties involved).
    # For property-specific results, use the AnalysisPropertyView's parsed_results
    parsed_results = JSONField(default=dict, blank=True)

    def getPropertyViewInfo(self):
        analysis_property_views = self.analysispropertyview_set.filter(analysis=self.id)
        return {
            'number_of_analysis_property_views': analysis_property_views.count(),
            'cycles': list(analysis_property_views.values_list('cycle', flat=True).distinct())
        }
