# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""
from django.db import models
from seed.models import Column

class DataAggregation(models.Model):
    name = models.CharField(max_length=255)
    column = models.ForeignKey(Column, on_delete=models.CASCADE)

    AVG = 0
    COUNT = 1
    MAX = 2
    MIN = 3 
    SUM = 4
    AGGREGATION_TYPES = (
        (AVG, 'Average'),
        (COUNT, 'Count'),
        (MAX, 'Max'),
        (MIN, 'Min'),
        (SUM, 'Sum'),
    )

    type = models.IntegerField(choices=AGGREGATION_TYPES)
