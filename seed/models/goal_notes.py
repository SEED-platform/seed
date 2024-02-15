"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.db import models

from seed.models import Goal, Property


class GoalNote(models.Model):
    QUESTION_CHOICES = (
        ('Is this a new construction or acquisition?', 'Is this a new construction or acquisition?'),
        ('Do you have data to report?', 'Do you have data to report?'),
        ('Is this value correct?', 'Is this value correct?'),
        ('Are these values correct?', 'Are these values correct?'),
        ('Other or multiple flags; explain in Additional Notes field', 'Other or multiple flags; explain in Additional Notes field'),
    )

    goal = models.ForeignKey(Goal, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)

    question = models.CharField(max_length=1024, choices=QUESTION_CHOICES, blank=True, null=True)
    resolution = models.CharField(max_length=1024, blank=True, null=True)
    passed_checks = models.BooleanField(default=False)
    new_or_acquired = models.BooleanField(default=False)

    def serialize(self):
        from seed.serializers.goal_notes import GoalNoteSerializer
        serializer = GoalNoteSerializer(self)
        return serializer.data
