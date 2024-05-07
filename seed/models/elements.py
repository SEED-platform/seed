# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""
import logging

from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from seed.models import Organization, Property, Uniformat

logger = logging.getLogger(__name__)


class Element(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, db_index=True)
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='elements', db_index=True)
    code = models.ForeignKey(Uniformat, on_delete=models.PROTECT, related_name='elements', db_index=True)
    element_id = models.CharField(max_length=36, null=True, db_index=True)
    description = models.TextField(null=True, db_collation='natural_sort')
    installation_date = models.DateField(null=True, db_index=True)
    condition_index = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100.0)], null=True)
    remaining_service_life = models.FloatField(null=True)
    replacement_cost = models.FloatField(validators=[MinValueValidator(0.0)], null=True)
    manufacturing_date = models.DateField(null=True)
    extra_data = models.JSONField(default=dict)

    # Potential future fields
    # - installation cost
    # - operation & maintenance cost
    # - annualized_lifecycle
    # - created/updated?

    class Meta:
        indexes = [
            GinIndex(fields=['extra_data'], name='extra_data_gin_idx'),
        ]
        ordering = ['-installation_date', 'description']
        unique_together = ['organization', 'element_id']
