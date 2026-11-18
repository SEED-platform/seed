"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models.salesforce_mappings import SalesforceMapping


class SalesforceMappingSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(required=True)

    def to_representation(self, instance):
        return super().to_representation(instance)

    def validate(self, attrs):
        column = attrs.get("column")
        organization_id = attrs.get("organization_id", getattr(self.instance, "organization_id", None))
        if column is not None and column.organization_id != organization_id:
            raise serializers.ValidationError({"column": "The selected column does not belong to this organization"})
        return attrs

    class Meta:
        model = SalesforceMapping
        fields = (
            "id",
            "organization_id",
            "column",
            "salesforce_fieldname",
        )
