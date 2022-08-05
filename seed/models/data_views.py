# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models import Column, Cycle, DataAggregation


class DataView(models.Model):
    name = models.CharField(max_length=255, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    filter_group = models.JSONField()
    cycles = models.ManyToManyField(Cycle)
    columns = models.ManyToManyField(Column)
    data_aggregations = models.ManyToManyField(DataAggregation)
