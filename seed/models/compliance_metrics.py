# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
"""

from datetime import datetime

from django.db import models
from django.utils import timezone

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column


class ComplianceMetric(models.Model):

    TARGET_GT_ACTUAL = 0  # example: GHG, Site EUI
    TARGET_LT_ACTUAL = 1  # example: EnergyStar Score
    METRIC_TYPES = (
        (TARGET_GT_ACTUAL, 'Target > Actual for Compliance'),
        (TARGET_LT_ACTUAL, 'Actual > Target for Compliance'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='compliance_metrics', blank=True, null=True)
    name = models.CharField(max_length=255)
    start = models.DateTimeField()  # only care about year, but adding as a DateTime
    end = models.DateTimeField()  # only care about year, but adding as a DateTime
    created = models.DateTimeField(auto_now_add=True)
    # TODO: could these be derived columns?
    actual_column = models.ForeignKey(Column, related_name="actual_column", blank=False, null=False, on_delete=models.CASCADE)
    target_column = models.ForeignKey(Column, related_name="target_column", blank=True, null=True, on_delete=models.CASCADE)
    metric_type = models.IntegerField(choices=METRIC_TYPES)
    x_axis_columns = models.ManyToManyField(Column, related_name="x_axis_columns")

    def __str__(self):
        return 'Compliance Metric - %s' % self.name

    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'

    # temporary until we have the metric setup page
    @classmethod
    def get_or_create_default(cls, organization):
        metric = ComplianceMetric.objects.filter(organization=organization).first()
        if not metric:
            name = 'Site EUI'
            actual_column = Column.objects.filter(column_name='Site EUI', organization=organization).first()
            target_column = Column.objects.filter(column_name='Target Site EUI', organization=organization).first()
            x_axes = Column.objects.filter(column_name__in=['Year Built', 'Property Type', 'Conditioned Floor Area'], organization=organization).all()

            # TODO: use of tzinfo does some weird stuff here and changes the year at the extremes...
            # saving as 2,2 since we don't care about day/month
            metric = ComplianceMetric.objects.create(
                name=name,
                organization=organization,
                start=datetime(2017, 2, 2, tzinfo=timezone.get_current_timezone()),
                end=datetime(2021, 2, 2, tzinfo=timezone.get_current_timezone()),
                actual_column=actual_column,
                target_column=target_column,
                metric_type=0
            )
            metric.x_axis_columns.set(x_axes)

        return metric
