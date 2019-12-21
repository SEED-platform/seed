# !/usr/bin/env python
# encoding: utf-8

from django.db import models
from django.contrib.postgres.fields import JSONField

from seed.lib.superperms.orgs.models import Organization


class ColumnMappingPreset(models.Model):
    name = models.CharField(max_length=255, blank=False)
    mappings = JSONField(default=list, blank=True)

    organizations = models.ManyToManyField(Organization)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
