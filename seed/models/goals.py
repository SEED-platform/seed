"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from seed.models import (
    AccessLevelInstance, 
    Column,
    Cycle, 
    Organization, 
)

class Goal(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    baseline_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='goal_baseline_cycles')
    current_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='goal_current_cycles')
    access_level_instance = models.ForeignKey(AccessLevelInstance, on_delete=models.CASCADE)
    column1 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_column1s')
    column2 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_column2s')
    column3 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='goal_column3s')
    # dont like validators? could use choices and define a list of integers 0-100
    target_percentage = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    name = models.CharField(max_length=255)

    # access_level_name 
    # NOT NECESSARY? its only used to select an ali_id. Just make it part of the create/edit process
    # these options are found in organization.access_level_names

    def __str__(self):
        return f"Goal - {self.name}"