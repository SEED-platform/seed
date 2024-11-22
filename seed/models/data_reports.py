"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from seed.models import AccessLevelInstance, Cycle, Organization

DATA_REPORT_TYPES = (
    ("standard", "standard"),
    ("transaction", "transaction"),
    ("multifamily", "multifamily"),
    ("water_treatment", "water_treatment"),
    ("data_center", "data_center"),
)


class DataReport(models.Model):
    name = models.CharField(max_length=255, unique=True)  # needs to be within org, not unique everywhere.
    type = models.CharField(max_length=50, choices=DATA_REPORT_TYPES, default="standard")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    baseline_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name="goal_baseline_cycles")
    current_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name="goal_current_cycles")
    access_level_instance = models.ForeignKey(AccessLevelInstance, on_delete=models.CASCADE)
    commitment_sqft = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    target_percentage = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    # OPR and WP percentage?
    # may have to be a function if type == multifamily

    def goals(self):
        return list(self.goalstandard_set.all()) + list(self.goaltransaction_set.all())

    def get_goal(self, goal_id):
        from seed.models import Goal

        if (goal := self.goalstandard_set.filter(id=goal_id).first()) or (goal := self.goaltransaction_set.filter(id=goal_id).first()):
            return goal
        else:
            raise Goal.DoesNotExist()

    """
    if standard, 1 standard goal
    if transaction, 1 transaction goal
    if multifamily, 2 standard goals (WB/OPR)
    if water_treatment, 1 standard goal, 1 water treatment goal, one streetlight goal
    if data_center, 1 datacenter goal
    """
