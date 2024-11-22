"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.core.exceptions import ValidationError
from rest_framework import serializers

from seed.models import Goal, GoalStandard, GoalTransaction


class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Goal
        fields = "__all__"

    def to_representation(self, obj):
        data = dict(super().to_representation(obj))
        if isinstance(obj, GoalStandard):
            child_data = GoalStandardSerializer(obj).data
            child_data["type"] = "standard"
            self.add_standard_data(obj, data)
        elif isinstance(obj, GoalTransaction):
            child_data = GoalTransactionSerializer(obj).data
            child_data["type"] = "transaction"
            self.add_transaction_data(obj, data)
        data["current_cycle_property_view_ids"] = obj.current_cycle_property_view_ids()
        data.update(child_data)
        return data

    def add_standard_data(self, obj, data):
        data.update(
            {
                "eui_column1_name": obj.eui_column1.display_name,
                "eui_column2_name": obj.eui_column2.display_name if obj.eui_column2 else None,
                "eui_column3_name": obj.eui_column3.display_name if obj.eui_column3 else None,
                "area_column_name": obj.area_column.display_name,
            }
        )

    def add_transaction_data(self, obj, data):
        self.add_standard_data
        data.update({"transaction_column_name": obj.transaction_column.display_name})


class GoalStandardSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalStandard
        fields = "__all__"

    def validate(self, data):
        return validate(data)


class GoalTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalTransaction
        fields = "__all__"

    def validate(self, data):
        return validate(data)


def validate(data):
    # non Null columns must be unique
    eui_columns = [data.get("eui_column1"), data.get("eui_column2"), data.get("eui_column3")]
    unique_columns = {column for column in eui_columns if column is not None}
    if len(unique_columns) < len([column for column in eui_columns if column is not None]):
        raise ValidationError("Columns must be unique.")
    return data
