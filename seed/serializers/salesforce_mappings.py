# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
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
