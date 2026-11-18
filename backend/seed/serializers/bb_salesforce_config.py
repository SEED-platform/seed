"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models import BBSalesforceConfig
from seed.serializers.base import EncryptedSecretField


class BBSalesforceConfigSerializer(serializers.ModelSerializer):
    client_secret = EncryptedSecretField(required=False, allow_blank=True, allow_null=True, trim_whitespace=True)

    class Meta:
        model = BBSalesforceConfig
        fields = (
            "organization",
            "salesforce_url",
            "client_id",
            "client_secret",
        )
