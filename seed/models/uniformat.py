# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import models


class Uniformat(models.Model):
    code = models.CharField(max_length=7, unique=True)
    category = models.CharField(max_length=100)
    definition = models.CharField(max_length=1024, null=True)
    imperial_units = models.CharField(max_length=10, null=True)
    metric_units = models.CharField(max_length=10, null=True)
    quantity_definition = models.CharField(max_length=100, null=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
