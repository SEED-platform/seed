# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import hashlib
import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from seed.data_importer.models import (
    TableColumnMapping,
    ImportRecord,
    SOURCE_FACILITY_ID_MAX_LEN,
)

_log = logging.getLogger(__name__)


class DataCoercionMapping(models.Model):
    table_column_mapping = models.ForeignKey(TableColumnMapping)
    source_string = models.TextField()
    source_type = models.CharField(max_length=50)
    destination_value = models.CharField(max_length=255, blank=True, null=True)
    destination_type = models.CharField(max_length=255, blank=True, null=True)
    is_mapped = models.BooleanField(default=False)
    confidence = models.FloatField(default=0)
    was_a_human_decision = models.BooleanField(default=False)
    valid_destination_value = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    def __unicode__(self, *args, **kwargs):
        return "%s (%s) -> %s (%s)" % (
            self.source_string, self.source_type, self.destination_value, self.destination_type,)

    def save(self, *args, **kwargs):
        try:
            assert self.destination_value is not None
            field = self.table_column_mapping.destination_django_field
            field.to_python(self.destination_value)
            if hasattr(field, "choices") and field.choices != []:
                assert self.destination_value in [f[0] for f in field.choices] or \
                    "%s" % self.destination_value in [f[0] for f in field.choices]
            self.valid_destination_value = True
        except BaseException:
            self.valid_destination_value = False
        self.is_mapped = (
            self.confidence > 0.6 or self.was_a_human_decision) and self.valid_destination_value
        super(DataCoercionMapping, self).save(*args, **kwargs)

    @property
    def source_string_sha(self):
        if not hasattr(self, "_source_string_sha"):
            m = hashlib.md5()
            m.update(self.source_string)
            self._source_string_sha = m.hexdigest()
        return self._source_string_sha


class ValidationRule(models.Model):
    table_column_mapping = models.ForeignKey(TableColumnMapping)
    passes = models.BooleanField(default=False)


class RangeValidationRule(ValidationRule):
    max_value = models.FloatField(blank=True, null=True)
    min_value = models.FloatField(blank=True, null=True)
    limit_min = models.BooleanField(default=False)
    limit_max = models.BooleanField(default=False)

    def __unicode__(self, *args, **kwargs):
        return "%s<x<%s" % (self.min_value, self.max_value,)


class ValidationOutlier(models.Model):
    rule = models.ForeignKey(ValidationRule)
    value = models.TextField(blank=True, null=True)


class BuildingImportRecord(models.Model):
    import_record = models.ForeignKey(ImportRecord)
    building_model_content_type = models.ForeignKey(ContentType, blank=True, null=True)
    building_pk = models.CharField(max_length=SOURCE_FACILITY_ID_MAX_LEN, blank=True, null=True)
    building_record = GenericForeignKey('building_model_content_type', 'building_pk')
    was_in_database = models.BooleanField(default=False)
    is_missing_from_import = models.BooleanField(default=False)

    def __unicode__(self, *args, **kwargs):
        return "%s" % self.building_record
