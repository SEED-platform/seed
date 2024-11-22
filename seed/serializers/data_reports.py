"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import DataReport
from seed.serializers.goals import GoalSerializer


class DataReportSerializer(serializers.ModelSerializer):
    goals = serializers.SerializerMethodField()

    class Meta:
        model = DataReport
        fields = "__all__"

    def get_goals(self, obj):
        goals = []
        for goalset in ["goalstandard_set", "goaltransaction_set"]:
            goals.extend(getattr(obj, goalset).all())

        data = GoalSerializer(goals, many=True).data
        return data

    def to_representation(self, obj):
        result = super().to_representation(obj)
        level_index = obj.access_level_instance.depth - 1
        details = {
            "level_name_index": level_index,
            "level_name": obj.organization.access_level_names[level_index],
            "baseline_cycle_name": obj.baseline_cycle.name,
            "current_cycle_name": obj.current_cycle.name,
        }
        result.update(details)
        return result

    def validate(self, data):
        # partial update allows a cycle or ali to be blank
        baseline_cycle = data.get("baseline_cycle") or self.instance.baseline_cycle
        current_cycle = data.get("current_cycle") or self.instance.current_cycle
        organization = data.get("organization") or self.instance.organization
        ali = data.get("access_level_instance") or self.instance.access_level_instance

        if baseline_cycle == current_cycle:
            raise ValidationError("Cycles must be unique.")

        if baseline_cycle.end > current_cycle.end:
            raise ValidationError("Baseline Cycle must precede Current Cycle.")

        if not all(
            [
                getattr(baseline_cycle, "organization", None) == organization,
                getattr(current_cycle, "organization", None) == organization,
                getattr(ali, "organization", None) == organization,
            ]
        ):
            raise ValidationError("Organization mismatch.")

        return data
