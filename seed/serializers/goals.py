"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import logging

from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import CycleGoal, Goal
from seed.serializers.cycles import CycleSerializer

logger = logging.getLogger(__name__)


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
            "eui_column1_name": self.get_column_name(obj.eui_column1),
            "eui_column2_name": self.get_column_name(obj.eui_column2),
            "eui_column3_name": self.get_column_name(obj.eui_column3),
            "area_column_name": self.get_column_name(obj.area_column),
        }
        if obj.type == "transaction":
            details["transactions_column_name"] = self.get_column_name(obj.transactions_column)
        result.update(details)

        if obj.partner_note_approval_user is not None:
            user = obj.partner_note_approval_user.user
            if user.first_name or user.last_name:
                result["partner_note_approval_user_name"] = user.get_full_name()
            else:
                result["partner_note_approval_user_name"] = user.username

        return result

    def validate(self, data):
        # partial update allows a cycle or ali to be blank
        baseline_cycle = data.get("baseline_cycle") or self.instance.baseline_cycle
        organization = data.get("organization") or self.instance.organization
        ali = data.get("access_level_instance") or self.instance.access_level_instance

        if not all(
            [
                getattr(baseline_cycle, "organization", None) == organization,
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

    def get_column_name(self, column):
        if not column:
            return None
        elif column.display_name:
            return column.display_name
        else:
            return column.column_name


class CycleGoalSerializer(serializers.ModelSerializer):
    goal = serializers.IntegerField(source="goal.id", read_only=True)

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["current_cycle"] = CycleSerializer(obj.current_cycle).data

        return result

    class Meta:
        model = CycleGoal
        fields = "__all__"
