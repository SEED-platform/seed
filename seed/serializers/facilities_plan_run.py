"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from drf_spectacular.extensions import OpenApiSerializerExtension
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from seed.models import Column, FacilitiesPlanRun
from seed.serializers.columns import ColumnSerializer


class FacilitiesPlanRunSerializer(serializers.ModelSerializer):
    columns = serializers.SerializerMethodField("get_columns", read_only=False)
    property_display_field = serializers.SerializerMethodField("get_property_display_field", read_only=False)
    run_at = serializers.DateTimeField("%Y-%m-%d %H:%M:%S %Z", read_only=True)
    display_columns = serializers.PrimaryKeyRelatedField(queryset=Column.objects.all(), many=True)
    ali_name = serializers.CharField(source="ali.name", read_only=True)
    ali_level = serializers.SerializerMethodField("get_ali_level", read_only=True)

    column_names = [
        "compliance_cycle_year_column",
        "include_in_total_denominator_column",
        "exclude_from_plan_column",
        "require_in_plan_column",
        "electric_energy_usage_column",
        "gas_energy_usage_column",
        "steam_energy_usage_column",
    ]

    class Meta:
        model = FacilitiesPlanRun
        fields = "__all__"

    @extend_schema_field(serializers.DictField(child=ColumnSerializer()))
    def get_columns(self, obj):
        facilities_plan = obj.facilities_plan
        nonnull_column_names = [c_name for c_name in self.column_names if getattr(facilities_plan, c_name, None) is not None]
        nonnull_columns = ColumnSerializer(
            [getattr(facilities_plan, c_name) for c_name in nonnull_column_names],
            many=True,
        ).data

        return dict(zip(nonnull_column_names, nonnull_columns, strict=False))

    @extend_schema_field(ColumnSerializer)
    def get_property_display_field(self, obj):
        org = obj.facilities_plan.organization
        property_display_field = Column.objects.filter(
            table_name="PropertyState", column_name=org.property_display_field, organization=org
        ).first()

        return ColumnSerializer(property_display_field).data

    def to_representation(self, obj):
        result = super().to_representation(obj)
        result["display_columns"] = ColumnSerializer(
            Column.objects.filter(id__in=result["display_columns"]),
            many=True,
        ).data

        return result

    def get_ali_level(self, obj) -> str:
        return obj.ali.organization.access_level_names[obj.ali.depth - 1]


class FacilitiesPlanRunSerializerExtension(OpenApiSerializerExtension):
    """`display_columns` is written as Column IDs, but read as serialized Columns (see `to_representation`)"""

    target_class = FacilitiesPlanRunSerializer

    def map_serializer(self, auto_schema, direction):
        schema = super().map_serializer(auto_schema, direction)
        if direction == "response":
            column = auto_schema.resolve_serializer(ColumnSerializer, direction)
            schema["properties"]["display_columns"] = {"type": "array", "items": column.ref}
        return schema
