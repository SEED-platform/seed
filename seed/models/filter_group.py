# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models.column_list_profiles import (
    VIEW_LIST_INVENTORY_TYPE,
    VIEW_LIST_PROPERTY
)
from seed.models.models import StatusLabel

AND = 0
LABEL_LOGIC_TYPE = [
    (AND, 'and'),
    (1, 'or'),
    (2, 'exclude'),
]


class FilterGroup(models.Model):

    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='filter_groups', null=False)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    query_dict = models.JSONField(null=False, default=dict)
    labels = models.ManyToManyField(StatusLabel)
    label_logic = models.IntegerField(choices=LABEL_LOGIC_TYPE, default=AND)

    class Meta:
        ordering = ['id']
        unique_together = ('name', 'organization')
