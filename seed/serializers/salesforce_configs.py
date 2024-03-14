# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

from rest_framework import serializers

from seed.models.salesforce_configs import SalesforceConfig


class SalesforceConfigSerializer(serializers.ModelSerializer):
    organization_id = serializers.IntegerField(required=True)

    class Meta:
        model = SalesforceConfig
        fields = (
            'id',
            'organization_id',
            'indication_label',
            'violation_label',
            'compliance_label',
            'account_rec_type',
            'contact_rec_type',
            'last_update_date',
            'unique_benchmark_id_fieldname',
            'seed_benchmark_id_column',
            'url',
            'username',
            'password',
            'security_token',
            'domain',
            'cycle_fieldname',
            'status_fieldname',
            'labels_fieldname',
            'contact_email_column',
            'contact_name_column',
            'account_name_column',
            'default_contact_account_name',
            'data_admin_name_column',
            'data_admin_email_column',
            'data_admin_account_name_column',
            'data_admin_contact_fieldname',
            'default_data_admin_account_name',
            'logging_email',
            'benchmark_contact_fieldname',
            'update_at_hour',
            'update_at_minute',
            'delete_label_after_sync'
        )
