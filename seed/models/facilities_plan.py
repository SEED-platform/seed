"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models import Column

logger = logging.getLogger(__name__)


class FacilitiesPlan(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    energy_running_sum_percentage = models.FloatField(default=0.75, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    compliance_cycle_year_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    include_in_total_denominator_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    exclude_from_plan_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    require_in_plan_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    gross_floor_area_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    building_category_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    electric_eui_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    gas_eui_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    steam_eui_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    total_eui_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    electric_energy_usage_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    gas_energy_usage_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    steam_energy_usage_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    electric_data_source_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")
    gas_data_source_column = models.ForeignKey(Column, on_delete=models.SET_NULL, blank=True, null=True, related_name="+")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_name_for_plan"),
        ]
