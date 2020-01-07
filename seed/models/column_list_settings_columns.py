# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from django.db import models

from seed.models import (
    Column,
    ColumnListSetting,
)


class ColumnListSettingColumn(models.Model):
    """Join table between column list settings and the column. Adds in pinned and index (order)"""

    column_list_setting = models.ForeignKey(ColumnListSetting, on_delete=models.CASCADE)
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    order = models.IntegerField(null=True)
    pinned = models.BooleanField(default=False)

    def __str__(self):
        return self.column_list_setting.name + " %s %s".format(self.order, self.pinned)
