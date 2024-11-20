"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from polymorphic.models import PolymorphicModel

from seed.models import Column, Property, PropertyView
from seed.models.data_reports import DataReport


class Goal(PolymorphicModel):
    def __str__(self):
        return f"Goal - {self.name}"

    def eui_columns(self):
        """Preferred column order"""
        eui_columns = [self.eui_column1, self.eui_column2, self.eui_column3]
        return [column for column in eui_columns if column]

    def properties(self):
        data_report = self.data_report
        properties = Property.objects.filter(
            Q(views__cycle=data_report.baseline_cycle) | Q(views__cycle=data_report.current_cycle),
            access_level_instance__lft__gte=data_report.access_level_instance.lft,
            access_level_instance__rgt__lte=data_report.access_level_instance.rgt,
        ).distinct()
        return properties

    def current_cycle_property_view_ids(self):
        view_ids = self.data_report.current_cycle.propertyview_set.all().values_list("id", flat=True)
        return list(view_ids)

class GoalStandard(Goal):
    name = models.CharField(max_length=255)
    data_report = models.ForeignKey(DataReport, on_delete=models.CASCADE)
    eui_column1 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="standard_eui_column1s")
    eui_column2 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="standard_eui_column2s", blank=True, null=True)
    eui_column3 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="standard_eui_column3s", blank=True, null=True)
    area_column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="standard_area_columns")

    class Meta:
        ordering = ["name"]

class GoalTransaction(Goal):
    name = models.CharField(max_length=255)
    data_report = models.ForeignKey(DataReport, on_delete=models.CASCADE)
    eui_column1 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="transaction_eui_column1s")
    eui_column2 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="transaction_eui_column2s", blank=True, null=True)
    eui_column3 = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="transaction_eui_column3s", blank=True, null=True)
    area_column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="transaction_area_columns")
    transaction_column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name="transaction_transaction_columns")
    # eui(t) is calced_kbtu/transactions

    class Meta:
        ordering = ["name"]

@receiver(post_save, sender=Goal)
@receiver(post_save, sender=GoalStandard)
@receiver(post_save, sender=GoalTransaction)
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