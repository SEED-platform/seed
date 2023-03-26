# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import Column, ColumnListProfile


class ColumnListProfileColumn(models.Model):
    """Join table between column list settings and the column. Adds in pinned and index (order)"""

    column_list_profile = models.ForeignKey(ColumnListProfile, on_delete=models.CASCADE)
    column = models.ForeignKey(Column, on_delete=models.CASCADE)
    order = models.IntegerField(null=True)
    pinned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.column_list_profile.name} {self.order} {self.pinned}"
