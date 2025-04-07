"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from seed.lib.superperms.orgs.models import Organization

logger = logging.getLogger(__name__)


class FacilitiesPlan(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    energy_running_sum_percentage = models.FloatField(default=0.75, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_name_for_plan"),
        ]
