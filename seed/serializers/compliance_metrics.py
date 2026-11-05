"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models.compliance_metrics import ComplianceMetric
from seed.serializers.base import ChoiceField


class ComplianceMetricSerializer(serializers.ModelSerializer):
    energy_metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES, required=False)
    emission_metric_type = ChoiceField(choices=ComplianceMetric.METRIC_TYPES, required=False)
    organization_id = serializers.IntegerField(required=True)

    organization_scoped_fields = (
        "cycles",
        "actual_energy_column",
        "target_energy_column",
        "actual_emission_column",
        "target_emission_column",
        "filter_group",
        "x_axis_columns",
    )

    def to_representation(self, instance):
        """Override the to_representation method to guarantee x_axis_columns sort order"""
        ret = super().to_representation(instance)
        ret["x_axis_columns"] = sorted(ret["x_axis_columns"])
        return ret

    def validate(self, attrs):
        """Reject cycles, columns, or a filter group of another organization"""
        org_id = attrs.get("organization_id", getattr(self.instance, "organization_id", None))
        errors = {}
        for field in self.organization_scoped_fields:
            value = attrs.get(field)
            if any(obj is not None and obj.organization_id != org_id for obj in (value if isinstance(value, list) else [value])):
                errors[field] = ["Must belong to the requested organization."]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    class Meta:
        model = ComplianceMetric
        fields = (
            "id",
            "name",
            "organization_id",
            "cycles",
            "actual_energy_column",
            "target_energy_column",
            "energy_metric_type",
            "actual_emission_column",
            "target_emission_column",
            "emission_metric_type",
            "filter_group",
            "x_axis_columns",
        )
