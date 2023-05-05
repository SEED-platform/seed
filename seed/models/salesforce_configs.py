# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import logging

from django.db import models

from seed.lib.superperms.orgs.models import Organization
from seed.models.columns import Column

logger = logging.getLogger(__name__)


class SalesforceConfig(models.Model):
    # Stores all the configuration needed to communicate with a Salesforce instance
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    indication_label = models.ForeignKey('seed.StatusLabel', on_delete=models.SET_NULL, null=True, related_name='indication_label')
    violation_label = models.ForeignKey('seed.StatusLabel', on_delete=models.SET_NULL, null=True, related_name='violation_label')
    compliance_label = models.ForeignKey('seed.StatusLabel', on_delete=models.SET_NULL, null=True, related_name='compliance_label')
    account_rec_type = models.CharField(blank=True, max_length=20, null=True)
    contact_rec_type = models.CharField(blank=True, max_length=20, null=True)
    last_update_date = models.DateTimeField(null=True, blank=True)
    unique_benchmark_id_fieldname = models.CharField(blank=True, max_length=128, null=True)
    seed_benchmark_id_column = models.ForeignKey(Column, related_name="benchmark_id_column", null=True, on_delete=models.CASCADE)
    url = models.CharField(blank=True, max_length=200, null=True)
    username = models.CharField(blank=True, max_length=128, null=True)
    password = models.CharField(blank=True, max_length=128, null=True)
    security_token = models.CharField(blank=True, max_length=128, null=True)
    domain = models.CharField(blank=True, max_length=50, null=True)
    cycle_fieldname = models.CharField(blank=True, max_length=128, null=True)
    status_fieldname = models.CharField(blank=True, max_length=128, null=True)
    labels_fieldname = models.CharField(blank=True, max_length=128, null=True)
    contact_email_column = models.ForeignKey(Column, related_name="contact_email_column", null=True, on_delete=models.CASCADE)
    contact_name_column = models.ForeignKey(Column, related_name="contact_name_column", null=True, on_delete=models.CASCADE)
    account_name_column = models.ForeignKey(Column, related_name="account_name_column", null=True, on_delete=models.CASCADE)
    default_contact_account_name = models.CharField(blank=True, max_length=200, null=True)
    benchmark_contact_fieldname = models.CharField(blank=True, max_length=128, null=True)
    data_admin_email_column = models.ForeignKey(Column, related_name="data_admin_email_column", null=True, on_delete=models.CASCADE)
    data_admin_name_column = models.ForeignKey(Column, related_name="data_admin_name_column", null=True, on_delete=models.CASCADE)
    data_admin_contact_fieldname = models.CharField(blank=True, max_length=128, null=True)
    data_admin_account_name_column = models.ForeignKey(Column, related_name="data_admin_account_name_column", null=True, on_delete=models.CASCADE)
    default_data_admin_account_name = models.CharField(blank=True, max_length=200, null=True)
    logging_email = models.CharField(blank=True, max_length=128, null=True)
    update_at_hour = models.IntegerField(blank=True, null=True)
    update_at_minute = models.IntegerField(blank=True, null=True)
    delete_label_after_sync = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="salesforce_update_at_hour_range",
                check=models.Q(update_at_hour__range=(0, 23)),
            ),
            models.CheckConstraint(
                name="salesforce_update_at_minute_range",
                check=models.Q(update_at_minute__range=(0, 59)),
            ),
        ]
