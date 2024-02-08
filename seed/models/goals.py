"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from seed.models import AccessLevelInstance, Column, Cycle, Organization


class Goal(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    baseline_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='goal_baseline_cycles')
    current_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='goal_current_cycles')
    access_level_instance = models.ForeignKey(AccessLevelInstance, on_delete=models.CASCADE)
    eui_column1 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_eui_column1s')
    # eui column 2 and 3 optional
    eui_column2 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_eui_column2s', blank=True, null=True)
    eui_column3 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_eui_column3s', blank=True, null=True)
    area_column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_area_columns')
    target_percentage = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"Goal - {self.name}"

    def eui_columns(self):
        """ Preferred column order """
        eui_columns = [self.eui_column1, self.eui_column2, self.eui_column3]
        return [column for column in eui_columns if column]
