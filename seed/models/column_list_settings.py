# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models

from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.models import (
    Column,
)


class ColumnListSetting(models.Model):
    """Ability to persist a list of views with different columns. The list of column views points to the columns that
    are contained in the list view."""

    VIEW_LIST = 0
    VIEW_DETAIL = 1
    VIEW_LOCATION_TYPES = [
        (VIEW_LIST, 'List View Settings'),
        (VIEW_DETAIL, 'Detail View Settings'),
    ]

    VIEW_LIST_PROPERTY = 0
    VIEW_LIST_TAXLOT = 1
    VIEW_LIST_INVENTORY_TYPE = [
        (VIEW_LIST_PROPERTY, 'Property'),
        (VIEW_LIST_TAXLOT, 'Tax Lot'),
    ]

    organization = models.ForeignKey(SuperOrganization, blank=True, null=True)
    name = models.CharField(max_length=512, db_index=True)
    settings_location = models.IntegerField(choices=VIEW_LOCATION_TYPES, default=VIEW_LIST)
    inventory_type = models.IntegerField(choices=VIEW_LIST_INVENTORY_TYPE, default=VIEW_LIST_PROPERTY)
    columns = models.ManyToManyField(Column, related_name='column_list_settings', through='seed.ColumnListSettingColumn')
