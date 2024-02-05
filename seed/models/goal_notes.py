"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import Goal, Property


class GoalNote(models.Model):
    QUESTION_CHOICES = (
        (1, 'Is this a new construction or acquisition?'),
        (2, 'Do you have data to report?'),
        (3, 'Is this value correct?'),
        (4, 'Are these values correct?'),
        (5, 'Other or multiple flags; explain in Additional Notes field'),
    )

    goal = models.ForeignKey(Goal, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)

    question = models.CharField(max_length=1024, choices=QUESTION_CHOICES, blank=True, null=True)
    resolution = models.CharField(max_length=1024, blank=True, null=True)
    passed_checks = models.BooleanField(default=False)
    new_or_acquired = models.BooleanField(default=False)
