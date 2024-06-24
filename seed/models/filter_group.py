"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models.column_list_profiles import VIEW_LIST_INVENTORY_TYPE, VIEW_LIST_PROPERTY
from seed.models.models import StatusLabel


class FilterGroup(models.Model):
    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="filter_groups", null=False)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    query_dict = models.JSONField(null=False, default=dict)
    and_labels = models.ManyToManyField(StatusLabel, related_name="and_filter_groups")
    or_labels = models.ManyToManyField(StatusLabel, related_name="or_filter_groups")
    exclude_labels = models.ManyToManyField(StatusLabel, related_name="exclude_filter_groups")

    class Meta:
        ordering = ["id"]
        unique_together = ("name", "organization")
