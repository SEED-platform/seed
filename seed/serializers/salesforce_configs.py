# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from rest_framework import serializers

from seed.models.salesforce_configs import SalesforceConfig


class SalesforceConfigSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(required=True)

    def to_representation(self, instance):

        return super().to_representation(instance)

    class Meta:
        model = SalesforceConfig
        fields = ('id', 'organization_id', 'indication_label', 'violation_label', 'compliance_label', 'account_rec_type', 'contact_rec_type',
                  'last_update_date', 'unique_benchmark_id_fieldname', 'seed_benchmark_id_column', 'url', 'username', 'password', 'security_token',
                  'domain', 'cycle_fieldname', 'status_fieldname', 'labels_fieldname', 'contact_email_column', 'contact_name_column',
                  'account_name_column', 'data_admin_name_column', 'data_admin_email_column')
