"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import Goal


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = "__all__"

    def to_representation(self, obj):
        result = super().to_representation(obj)
        level_index = obj.access_level_instance.depth - 1

        details = {
            "level_name_index": level_index,
            "level_name": obj.organization.access_level_names[level_index],
            "baseline_cycle_name": obj.baseline_cycle.name,
            "current_cycle_name": obj.current_cycle.name,
            "eui_column1_name": obj.eui_column1.display_name,
            "eui_column2_name": obj.eui_column2.display_name if obj.eui_column2 else None,
            "eui_column3_name": obj.eui_column3.display_name if obj.eui_column3 else None,
            "area_column_name": obj.area_column.display_name,
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

        # non Null columns must be unique
        eui_columns = [data.get("eui_column1"), data.get("eui_column2"), data.get("eui_column3")]
        unique_columns = {column for column in eui_columns if column is not None}
        if len(unique_columns) < len([column for column in eui_columns if column is not None]):
            raise ValidationError("Columns must be unique.")

        return data
