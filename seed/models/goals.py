"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

from seed.models import AccessLevelInstance, Column, Cycle, Organization, Property

GOAL_TYPE_CHOICES = (
    ("standard", "standard"),
    ("transaction", "transaction"),
)


class Goal(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    baseline_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name="goal_baseline_cycles")
    current_cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name="goal_current_cycles")
    access_level_instance = models.ForeignKey(AccessLevelInstance, on_delete=models.CASCADE)
    eui_column1 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="goal_eui_column1s")
    # eui column 2 and 3 optional
    eui_column2 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="goal_eui_column2s", blank=True, null=True)
    eui_column3 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="goal_eui_column3s", blank=True, null=True)
    area_column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="goal_area_columns")
    target_percentage = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    commitment_sqft = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0)])
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=GOAL_TYPE_CHOICES, default="standard")
    transactions_column = models.ForeignKey(
        Column, on_delete=models.CASCADE, related_name="goal_transactions_columns", blank=True, null=True
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_goal_name_per_organization"),
        ]

    def save(self, *args, **kwargs):
        if self.type == "standard":
            self.transactions_column = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Goal - {self.name}"

    def eui_columns(self):
        """Preferred column order"""
        eui_columns = [self.eui_column1, self.eui_column2, self.eui_column3]
        return [column for column in eui_columns if column]

    def properties(self):
        properties = Property.objects.filter(
            Q(views__cycle=self.baseline_cycle) | Q(views__cycle=self.current_cycle),
            access_level_instance__lft__gte=self.access_level_instance.lft,
            access_level_instance__rgt__lte=self.access_level_instance.rgt,
        ).distinct()

        return properties


@receiver(post_save, sender=Goal)
def post_save_goal(sender, instance, **kwargs):
    from seed.models import GoalNote

    # retrieve a flat set of all property ids associated with this goal
    goal_property_ids = set(instance.properties().values_list("id", flat=True))

    # retrieve a flat set of all property ids from the previous goal (through goal note which has not been created/updated yet)
    previous_property_ids = set(instance.goalnote_set.values_list("property_id", flat=True))

    # create, or update has added more properties to the goal
    new_property_ids = goal_property_ids - previous_property_ids
    # update has removed properties from the goal
    removed_property_ids = previous_property_ids - goal_property_ids

    if new_property_ids:
        new_goal_notes = [GoalNote(goal=instance, property_id=id) for id in new_property_ids]
        GoalNote.objects.bulk_create(new_goal_notes)

    if removed_property_ids:
        GoalNote.objects.filter(goal=instance, property_id__in=removed_property_ids).delete()
