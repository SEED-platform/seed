"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models

from seed.lib.superperms.orgs.models import AccessLevelInstance, Organization
from seed.models.cycles import Cycle
from seed.models.filter_group import FilterGroup


class ReportConfiguration(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="report_configurations", null=False)
    x_column = models.CharField(max_length=255, null=True)
    y_column = models.CharField(max_length=255, null=True)
    cycles = models.ManyToManyField(Cycle, related_name="report_configurations")
    filter_group = models.ForeignKey(FilterGroup, on_delete=models.CASCADE, related_name="report_configurations", null=True)
    access_level_instance = models.ForeignKey(
        AccessLevelInstance, on_delete=models.CASCADE, related_name="report_configurations", null=True
    )
    access_level_depth = models.IntegerField(null=True)
