# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from seed.lib.superperms.orgs.models import Organization


class AuditTemplateConfig(models.Model):
    # Stores all the configuration needed to communicate with Audit Template
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE)
    update_at_day = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(6)])
    update_at_hour = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(23)])
    update_at_minute = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(59)])
    last_update_date = models.DateTimeField(null=True, blank=True)
