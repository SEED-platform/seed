# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models.salesforce_mappings import SalesforceMapping


class SalesforceMappingSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(required=True)

    def to_representation(self, instance):

        return super().to_representation(instance)

    class Meta:
        model = SalesforceMapping
        fields = ('id', 'organization_id', 'column', 'salesforce_fieldname',)
