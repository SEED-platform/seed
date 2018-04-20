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

    organization = models.ForeignKey(SuperOrganization, blank=True, null=True)
    name = models.CharField(max_length=512, db_index=True)
    columns = models.ManyToManyField(Column)
