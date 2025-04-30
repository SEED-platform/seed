"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import Column, FacilitiesPlanRun
from seed.serializers.columns import ColumnSerializer


class FacilitiesPlanRunSerializer(serializers.ModelSerializer):
    columns = serializers.SerializerMethodField("get_columns", read_only=False)
    run_at = serializers.DateTimeField("%Y-%m-%d %H:%M:%S %Z", read_only=True)
    display_columns = serializers.PrimaryKeyRelatedField(queryset=Column.objects.all(), many=True)

    column_names = [
        "compliance_cycle_year_column",
        "include_in_total_denominator_column",
        "exclude_from_plan_column",
        "require_in_plan_column",
        "gross_floor_area_column",
        "building_category_column",
        "electric_eui_column",
        "gas_eui_column",
        "steam_eui_column",
        "total_eui_column",
        "electric_energy_usage_column",
        "gas_energy_usage_column",
        "gas_energy_usage_column",
    ]

    class Meta:
        model = FacilitiesPlanRun
        fields = "__all__"

    def get_columns(self, obj):
        facilities_plan = obj.facilities_plan
        nonnull_column_names = [c_name for c_name in self.column_names if getattr(facilities_plan, c_name, None) is not None]
        nonnull_columns = ColumnSerializer(
            [getattr(facilities_plan, c_name) for c_name in nonnull_column_names],
            many=True,
        ).data

        return dict(zip(nonnull_column_names, nonnull_columns))

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["display_columns"] = ColumnSerializer(
            Column.objects.filter(id__in=result["display_columns"]),
            many=True,
        ).data

        return result
