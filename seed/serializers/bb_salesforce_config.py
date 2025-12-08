"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import BBSalesforceConfig


class BBSalesforceConfigSerializer(serializers.ModelSerializer):
    # organization_id = serializers.PrimaryKeyRelatedField(source="organization", read_only=True)

    class Meta:
        model = BBSalesforceConfig
        fields = (
            "organization",
            "salesforce_url",
            "client_id",
            "client_secret",
        )
