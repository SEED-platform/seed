"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from itertools import chain

from seed.models import AccessLevelInstance, Column, Cycle, Organization, Property


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


@receiver(post_save, sender=Goal)
def post_save_goal(sender, instance, created, **kwargs):
    if created:
        from seed.models import GoalNote
        # GoalNote requires goal and property. Find a list of properties associated with either cycle.
        baseline_property_ids = instance.baseline_cycle.propertyview_set.values_list('property_id', flat=True)
        current_property_ids = instance.current_cycle.propertyview_set.values_list('property_id', flat=True)
        property_ids = set(chain(baseline_property_ids, current_property_ids))
        properties = Property.objects.filter(id__in=property_ids)
        default_goal_note = {'goal': instance}

        for property in properties:
            default_goal_note['property'] = property
            GoalNote.objects.create(**default_goal_note)

