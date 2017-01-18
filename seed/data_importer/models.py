# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import csv
import datetime
import hashlib
import json
import math
import tempfile
from urllib import unquote

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.timesince import timesince
from django_extensions.db.models import TimeStampedModel

from config.utils import de_camel_case
from seed.data_importer.managers import NotDeletedManager
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.utils.cache import (
    set_cache_raw, set_cache_state, get_cache, get_cache_raw,
    get_cache_state, delete_cache
)

SOURCE_FACILITY_ID_MAX_LEN = 40

STATUS_UPLOADING = 0
STATUS_MACHINE_MAPPING = 1
STATUS_MAPPING = 2
STATUS_MACHINE_CLEANING = 3
STATUS_CLEANING = 4
STATUS_READY_TO_PRE_MERGE = 5
STATUS_PRE_MERGING = 6
STATUS_READY_TO_MERGE = 7
STATUS_MERGING = 8
STATUS_LIVE = 9
STATUS_UNKNOWN = 10
STATUS_MATCHING = 11

# TODO: use these instead of the others defined in models.py
IMPORT_STATII = [
    (STATUS_UPLOADING, "Uploading"),
    (STATUS_MACHINE_MAPPING, "Machine Mapping"),
    (STATUS_MAPPING, "Needs Mapping"),
    (STATUS_MACHINE_CLEANING, "Machine Cleaning"),
    (STATUS_CLEANING, "Needs Cleaning"),
    (STATUS_READY_TO_PRE_MERGE, "Ready to Merge"),
    (STATUS_PRE_MERGING, "Merging"),
    (STATUS_READY_TO_MERGE, "Merge Complete"),
    (STATUS_MERGING, "Importing"),
    (STATUS_LIVE, "Live"),
    (STATUS_UNKNOWN, "Unknown"),
    (STATUS_MATCHING, "Matching")
]


class DuplicateDataError(RuntimeError):
    def __init__(self, id):
        super(DuplicateDataError, self).__init__()
        self.id = id


class NotDeletableModel(models.Model):
    deleted = models.BooleanField(default=False)

    objects = NotDeletedManager()
    default_manager = NotDeletedManager()
    raw_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.save()

    class Meta:
        abstract = True


class ImportRecord(NotDeletableModel):
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name Your Dataset",
                            default="Unnamed Dataset")
    app = models.CharField(max_length=64, blank=False, null=False, verbose_name='Destination App',
                           help_text='The application (e.g. BPD or SEED) for this dataset',
                           default='seed')
    owner = models.ForeignKey('landing.SEEDUser', blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    finish_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)
    last_modified_by = models.ForeignKey('landing.SEEDUser', related_name="modified_import_records",
                                         blank=True,
                                         null=True)
    notes = models.TextField(blank=True, null=True)
    merge_analysis_done = models.BooleanField(default=False)
    merge_analysis_active = models.BooleanField(default=False)
    merge_analysis_queued = models.BooleanField(default=False)
    premerge_analysis_done = models.BooleanField(default=False)
    premerge_analysis_active = models.BooleanField(default=False)
    premerge_analysis_queued = models.BooleanField(default=False)
    matching_active = models.BooleanField(default=False)
    matching_done = models.BooleanField(default=False)
    is_imported_live = models.BooleanField(default=False)
    keep_missing_buildings = models.BooleanField(default=True)
    status = models.IntegerField(default=0, choices=IMPORT_STATII)
    import_completed_at = models.DateTimeField(blank=True, null=True)
    merge_completed_at = models.DateTimeField(blank=True, null=True)
    mcm_version = models.IntegerField(blank=True, null=True)
    super_organization = models.ForeignKey(
        SuperOrganization, blank=True, null=True, related_name='import_records'
    )

    # destination_taxonomy = models.ForeignKey('lin.Taxonomy', blank=True, null=True)
    # source_taxonomy = models.ForeignKey('lin.Taxonomy', blank=True, null=True)

    def __unicode__(self):
        return "ImportRecord %s: %s, started at %s" % (self.pk, self.name, self.start_time)

    class Meta:
        ordering = ("-updated_at",)

    def delete(self, *args, **kwargs):
        super(ImportRecord, self).delete(*args, **kwargs)
        for f in self.files:
            f.delete()

    @property
    def files(self):
        return self.importfile_set.all().order_by("file")

    @property
    def num_files(self):
        if not hasattr(self, "_num_files"):
            self._num_files = self.importfile_set.count()
        return self._num_files

    @property
    def num_files_mapped(self):
        return self.files.filter(num_mapping_errors=0, initial_mapping_done=True).count()

    @property
    def num_files_to_map(self):
        return self.num_files - self.num_files_mapped

    @property
    def percent_files_mapped(self):
        if self.num_files > 0:
            return int(round(100.0 * self.num_files_mapped / self.num_files))
        return 0

    @property
    def num_files_cleaned(self):
        return self.files.filter(coercion_mapping_done=True, num_coercion_errors=0).count()

    @property
    def num_files_to_clean(self):
        return self.num_files - self.num_files_cleaned

    @property
    def percent_files_cleaned(self):
        if self.num_files > 0:
            return int(round(100.0 * self.num_files_cleaned / self.num_files))
        return 0

    @property
    def num_files_merged(self):
        return self.num_ready_for_import

    @property
    def num_files_to_merge(self):
        return self.num_not_ready_for_import

    @property
    def percent_files_ready_to_merge(self):
        if self.num_files > 0:
            return int(round(100.0 * self.num_files_merged / self.num_files))
        return 0

    @property
    def num_ready_for_import(self):
        if not hasattr(self, "_num_ready_for_import"):
            completed = 0
            for f in self.files:
                if f.ready_to_import:
                    completed += 1
            self._num_ready_for_import = completed

        return self._num_ready_for_import

    @property
    def num_not_ready_for_import(self):
        return self.num_files - self.num_ready_for_import

    @property
    def ready_for_import(self):
        return self.num_not_ready_for_import == 0

    @property
    def percent_ready_for_import_by_file_count(self):
        try:
            percent_ready = 100.00 * self.num_ready_for_import / self.num_files
        except ZeroDivisionError:
            percent_ready = 0
        return percent_ready

    @property
    def percent_ready_for_import(self):
        if not hasattr(self, "_percent_ready_for_import"):
            total = 0
            completed = 0
            for f in self.files:
                total += f.num_tasks_total or 0
                completed += f.num_tasks_complete or 0
            if total == 0:
                self._percent_ready_for_import = 0
            else:
                self._percent_ready_for_import = math.floor(100.0 * completed / total)

        return self._percent_ready_for_import

    @property
    def num_failed_tablecolumnmappings(self):
        if not hasattr(self, "_num_failed_tablecolumnmappings"):
            total = 0
            for f in self.files:
                total += f.num_failed_tablecolumnmappings
            self._num_failed_tablecolumnmappings = total
        return self._num_failed_tablecolumnmappings

    @property
    def num_coercion_errors(self):
        if not hasattr(self, "_num_failed_num_coercion_errors"):
            total = 0
            for f in self.files:
                total += f.num_coercion_errors

            self._num_failed_num_coercion_errors = total
        return self._num_failed_num_coercion_errors

    @property
    def num_validation_errors(self):
        if not hasattr(self, "_num_failed_validation_errors"):
            total = 0
            for f in self.files:
                total += f.num_validation_errors
            self._num_failed_validation_errors = total
        return self._num_failed_validation_errors

    @property
    def num_rows(self):
        if not hasattr(self, "_num_rows"):
            total = 0
            for f in self.files:
                total += f.num_rows
            self._num_rows = total
        return self._num_rows

    @property
    def num_columns(self):
        if not hasattr(self, "_num_columns"):
            total = 0
            for f in self.files:
                total += f.num_columns
            self._num_columns = total
        return self._num_columns

    @property
    def total_file_size(self):
        if not hasattr(self, "_total_file_size"):
            total = 0
            for f in self.files:
                total += f.file_size_in_bytes
            self._total_file_size = total
        return self._total_file_size

    @property
    def total_correct_mappings(self):
        if self.percent_ready_for_import != 100:
            return (100 / (100 - self.percent_ready_for_import)) * (
                self.num_validation_errors + self.num_coercion_errors + self.num_failed_tablecolumnmappings)
        else:
            return 100

    @property
    def merge_progress_key(self):
        """
        Cache key used to track percentage completion for merge task.
        """
        return "merge_progress_pct_%s" % self.pk

    @property
    def match_progress_key(self):
        """
        Cache key used to track percentage completion for merge task.
        """
        return "match_progress_pct_%s" % self.pk

    @property
    def merge_status_key(self):
        """
        Cache key used to set/get status messages for merge task.
        """
        return "merge_import_record_status_%s" % self.pk

    @property
    def pct_merge_complete(self):
        return get_cache(self.merge_progress_key)['progress']

    @property
    def merge_seconds_remaining_key(self):
        return "merge_seconds_remaining_%s" % self.pk

    @property
    def premerge_progress_key(self):
        return "premerge_progress_pct_%s" % self.pk

    @property
    def pct_premerge_complete(self):
        return get_cache(self.premerge_progress_key)['progress']

    @property
    def premerge_seconds_remaining_key(self):
        return "premerge_seconds_remaining_%s" % self.pk

    @property
    def MAPPING_ACTIVE_KEY(self):
        return "IR_MAPPING_ACTIVE%s" % self.pk

    @property
    def MAPPING_QUEUED_KEY(self):
        return "IR_MAPPING_QUEUED%s" % self.pk

    @property
    def estimated_seconds_remaining(self):
        return get_cache_raw(self.merge_seconds_remaining_key)

    @property
    def merge_status(self):
        return get_cache(self.merge_status_key)['status']

    @property
    def premerge_estimated_seconds_remaining(self):
        return get_cache_raw(self.premerge_seconds_remaining_key)

    @property
    def matched_buildings(self):
        return self.buildingimportrecord_set.filter(was_in_database=True,
                                                    is_missing_from_import=False)

    @property
    def num_matched_buildings(self):
        return self.matched_buildings.count()

    @property
    def new_buildings(self):
        return self.buildingimportrecord_set.filter(was_in_database=False,
                                                    is_missing_from_import=False)

    @property
    def num_new_buildings(self):
        return self.new_buildings.count()

    @property
    def missing_buildings(self):
        return self.buildingimportrecord_set.filter(is_missing_from_import=True)

    @property
    def num_missing_buildings(self):
        return self.missing_buildings.count()

    @property
    def num_buildings_imported_total(self):
        return self.buildingimportrecord_set.all().count()

    @property
    def status_percent(self):
        if self.status == STATUS_MACHINE_CLEANING:
            total_percent = 0
            num_mapping = 0
            for f in self.files:
                if f.cleaning_progress_pct and f.num_columns is not None and f.num_rows is not None:
                    total_percent += f.cleaning_progress_pct * f.num_columns * f.num_rows
                    num_mapping += 100.0 * f.num_columns * f.num_rows
            if num_mapping > 0:
                return 100.0 * total_percent / num_mapping
            else:
                return 0
        elif self.status == STATUS_CLEANING or self.status == STATUS_MAPPING:
            return 100.0 * self.status_numerator / self.status_denominator
        elif self.premerge_analysis_active:
            return self.pct_premerge_complete or 100.0
        elif self.merge_analysis_active:
            return self.pct_merge_complete or 100.0
        elif self.is_imported_live:
            return 100.0
        else:
            return self.percent_files_ready_to_merge

    @property
    def status_numerator(self):
        if self.status == STATUS_CLEANING:
            return self.num_files_cleaned
        elif self.status == STATUS_MAPPING:
            return self.num_files_mapped
        return 0

    @property
    def status_denominator(self):
        return self.num_files

    # URLS
    @property
    def app_namespace(self):
        if self.app == 'bpd':
            return 'data_importer'
        else:
            return self.app

    @property
    def pre_merge_url(self):
        return reverse("%s:start_pre_merge" % self.app_namespace, args=(self.pk,))

    @property
    def worksheet_url(self):
        return reverse("%s:worksheet" % self.app_namespace, args=(self.pk,))

    @property
    def add_files_url(self):
        return reverse("%s:new_import" % self.app_namespace, args=(self.pk,))

    @property
    def status_url(self):
        if self.status <= STATUS_READY_TO_PRE_MERGE:
            return self.worksheet_url
        elif self.status < STATUS_READY_TO_MERGE:
            return self.premerge_progress_url
        elif self.status < STATUS_MERGING:
            return self.start_merge_url
        elif self.status < STATUS_LIVE:
            return self.merge_progress_url
        else:
            return self.worksheet_url

    @property
    def is_not_in_progress(self):
        return self.status < STATUS_LIVE

    @property
    def premerge_progress_url(self):
        return reverse("data_importer:pre_merge", args=(self.pk,))

    @property
    def merge_progress_url(self):
        return reverse("data_importer:merge_progress", args=(self.pk,))

    @property
    def start_merge_url(self):
        return reverse("%s:merge" % self.app_namespace, args=(self.pk,))

    @property
    def merge_url(self):
        return reverse("%s:merge" % self.app_namespace, args=(self.pk,))

    @property
    def dashboard_url(self):
        return reverse("%s:dashboard" % self.app_namespace, args=(self.pk,))

    @property
    def search_url(self):
        return reverse("data_importer:search", args=(self.pk,))

    @property
    def delete_url(self):
        return reverse("%s:delete" % self.app_namespace, args=(self.pk,))

    @property
    def save_import_meta_url(self):
        return reverse("data_importer:save_import_meta", args=(self.pk,))

    @property
    def display_as_in_progress(self):
        return self.status in [STATUS_MACHINE_MAPPING, STATUS_MACHINE_CLEANING, STATUS_PRE_MERGING,
                               STATUS_MERGING]

    @property
    def is_mapping_or_cleaning(self):
        return self.status in [STATUS_MAPPING, STATUS_CLEANING, ]

    @property
    def status_is_live(self):
        return self.status == STATUS_LIVE

    def mark_merged(self):
        """
        Marks the ImportRecord as having been processed (via merge_import_record())
        """
        self.merge_analysis_done = True
        self.merge_analysis_active = False
        self.is_imported_live = True
        self.import_completed_at = datetime.datetime.now()
        self.save()

    def mark_merge_started(self):
        """
        Marks the ImportRecord as having a merge in progress.
        """
        self.merge_analysis_done = False
        self.merge_analysis_active = True
        self.merge_analysis_queued = False
        self.save()

    @property
    def summary_analysis_active(self):
        return get_cache_state(self.__class__.SUMMARY_ANALYSIS_ACTIVE_KEY(self.pk), False)

    @property
    def summary_analysis_queued(self):
        return get_cache_state(self.__class__.SUMMARY_ANALYSIS_QUEUED_KEY(self.pk), False)

    @classmethod
    def SUMMARY_ANALYSIS_ACTIVE_KEY(cls, pk):
        return "SUMMARY_ANALYSIS_ACTIVE%s" % pk

    @classmethod
    def SUMMARY_ANALYSIS_QUEUED_KEY(cls, pk):
        return "SUMMARY_ANALYSIS_QUEUED%s" % pk

    @property
    def form(self, data=None):
        from seed.data_importer import ImportRecordForm
        return ImportRecordForm(data, instance=self)

    def prefixed_pk(self, pk, max_len_before_prefix=(SOURCE_FACILITY_ID_MAX_LEN - len('IMP1234-'))):
        """This is a total hack to support prefixing until source_facility_id
        is turned into a proper pk.  Prefixes a given pk with the import_record"""
        if len("%s" % pk) > max_len_before_prefix:
            m = hashlib.md5()
            m.update(pk)
            digest = m.hexdigest()
            # TODO: precompute this if condition based on md5 alg and SFID MAX LEN
            if len(digest) > max_len_before_prefix:
                digest = digest[:max_len_before_prefix]
            transformed_pk = digest
        else:
            transformed_pk = pk
        return "IMP%s-%s" % (self.pk, transformed_pk)

    @property
    def to_json(self):
        try:
            last_modified_by = ""
            try:
                if self.last_modified_by:
                    last_modified_by = self.last_modified_by.email or ""
            except User.DoesNotExist:
                pass
            return json.dumps({
                'name': self.name,
                'app': self.app,
                'last_modified_time_ago': timesince(self.updated_at).split(",")[0],
                'last_modified_seconds_ago': -1 * (
                    self.updated_at - datetime.datetime.now()).total_seconds(),
                'last_modified_by': last_modified_by,
                'notes': self.notes,
                'merge_analysis_done': self.merge_analysis_done,
                'merge_analysis_active': self.merge_analysis_active,
                'merge_analysis_queued': self.merge_analysis_queued,
                'premerge_analysis_done': self.premerge_analysis_done,
                'premerge_analysis_active': self.premerge_analysis_active,
                'premerge_analysis_queued': self.premerge_analysis_queued,
                'matching_active': self.matching_active,
                'matching_done': self.matching_done,
                'is_imported_live': self.is_imported_live,
                'num_files': self.num_files,
                'keep_missing_buildings': self.keep_missing_buildings,
                'dashboard_url': self.dashboard_url,
                'delete_url': self.delete_url,
                'search_url': self.search_url,
                'status_url': self.status_url,
                'display_as_in_progress': self.display_as_in_progress,
                'worksheet_url': self.worksheet_url,
                'is_not_in_progress': self.is_not_in_progress,
                'save_import_meta_url': self.save_import_meta_url,
                'percent_files_ready_to_merge': self.percent_files_ready_to_merge,
                'status': self.status,
                'status_text': IMPORT_STATII[self.status][1],
                'status_percent': round(self.status_percent, 0),
                'status_numerator': self.status_numerator,
                'status_denominator': self.status_denominator,
                'status_is_live': self.status_is_live,
                'is_mapping_or_cleaning': self.is_mapping_or_cleaning,
                'num_buildings_imported_total': self.num_buildings_imported_total,
            })
        except:
            from traceback import print_exc
            print_exc()
            return {}

    @property
    def worksheet_progress_json(self):
        progresses = []
        some_file_has_mapping_active = not get_cache_state(self.MAPPING_ACTIVE_KEY, False)
        try:
            for f in self.files:
                progresses.append({
                    'pk': f.pk,
                    'filename': f.filename_only,
                    'delete_url': reverse("%s:delete_file" % self.app_namespace, args=(f.pk,)),
                    'mapping_url': reverse("%s:mapping" % self.app_namespace, args=(f.pk,)),
                    'cleaning_url': reverse("%s:cleaning" % self.app_namespace, args=(f.pk,)),
                    'matching_url': reverse("%s:matching" % self.app_namespace, args=(f.pk,)),
                    'num_columns': f.num_columns,
                    'num_rows': f.num_rows,
                    'num_mapping_complete': f.num_mapping_complete,
                    'num_mapping_total': f.num_mapping_total,
                    'num_mapping_remaining': f.num_mapping_remaining,
                    'mapping_active': f.mapping_active,
                    'some_file_has_mapping_active': some_file_has_mapping_active,
                    'coercion_mapping_active': f.coercion_mapping_active,
                    'cleaning_progress_pct': round(f.cleaning_progress_pct, 1),
                    'num_cleaning_remaining': f.num_cleaning_remaining,
                    'num_cleaning_complete': f.num_cleaning_complete,
                    'num_cleaning_total': f.num_cleaning_total,
                    'export_ready': f.export_ready,
                    'export_generation_pct_complete': int(round(f.export_generation_pct_complete)),
                    'export_url': f.export_url,
                    'worksheet_url': self.worksheet_url,
                    'generate_url': f.generate_url,
                    'premerge_progress_url': f.premerge_progress_url,
                    'merge_progress_url': f.merge_progress_url,
                    'force_restart_cleaning_url': f.force_restart_cleaning_url,
                    'is_espm': f.is_espm,
                })
        except:
            from traceback import print_exc
            print_exc()
        return json.dumps(progresses)


class ImportFile(NotDeletableModel, TimeStampedModel):
    import_record = models.ForeignKey(ImportRecord)
    cycle = models.ForeignKey('seed.Cycle', blank=True, null=True)
    file = models.FileField(
        upload_to="data_imports", max_length=500, blank=True, null=True
    )
    # Save the name of the raw file that was uploaded before it was saved to disk with the unique
    # extension.
    uploaded_filename = models.CharField(blank=True, max_length=255)
    file_size_in_bytes = models.IntegerField(blank=True, null=True)
    export_file = models.FileField(
        upload_to="data_imports/exports", blank=True, null=True
    )
    cached_first_row = models.TextField(blank=True, null=True)
    # Save a list of the final column mapping names that were used for this file.
    # This should really be a many-to-many with the column/ColumnMapping table.
    cached_mapped_columns = models.TextField(blank=True, null=True)
    cached_second_to_fifth_row = models.TextField(blank=True, null=True)
    has_header_row = models.BooleanField(default=True)
    mapping_completion = models.IntegerField(blank=True, null=True)
    mapping_done = models.BooleanField(default=False)
    mapping_error_messages = models.TextField(blank=True, null=True)
    matching_completion = models.IntegerField(blank=True, null=True)
    matching_done = models.BooleanField(default=False)
    num_coercion_errors = models.IntegerField(blank=True, null=True, default=0)
    num_coercions_total = models.IntegerField(blank=True, null=True, default=0)
    num_columns = models.IntegerField(blank=True, null=True)
    num_mapping_errors = models.IntegerField(default=0)
    num_mapping_warnings = models.IntegerField(default=0)
    num_rows = models.IntegerField(blank=True, null=True)
    num_tasks_complete = models.IntegerField(blank=True, null=True)
    num_tasks_total = models.IntegerField(blank=True, null=True)
    num_validation_errors = models.IntegerField(blank=True, null=True)
    # New MCM values
    raw_save_done = models.BooleanField(default=False)
    raw_save_completion = models.IntegerField(blank=True, null=True)
    source_type = models.CharField(null=True, blank=True, max_length=63)
    # program names should match a value in common.mapper.Programs
    source_program = models.CharField(blank=True, max_length=80)  # don't think that this is used
    # program version is in format "x.y[.z]"
    source_program_version = models.CharField(blank=True, max_length=40)  # don't think this is used

    def __unicode__(self):
        return "%s" % self.file.name

    def save(self, in_validation=False, *args, **kwargs):
        super(ImportFile, self).save(*args, **kwargs)
        try:
            if not in_validation:
                queue_update_status_for_import_record(self.import_record.pk)
        except ImportRecord.DoesNotExist:
            pass
            # If we're deleting.

    @property
    def from_portfolio_manager(self):
        return self._strcmp(self.source_program, 'PortfolioManager')

    def _strcmp(self, a, b, ignore_ws=True, ignore_case=True):
        """Easily controlled loose string-matching."""
        if ignore_ws:
            a, b = a.strip(), b.strip()
        if ignore_case:
            a, b = a.lower(), b.lower()
        return a == b

    @property
    def local_file(self):
        if not hasattr(self, "_local_file"):
            temp_file = tempfile.NamedTemporaryFile(mode='w+b', bufsize=1024, delete=False)
            for chunk in self.file.chunks(1024):
                temp_file.write(chunk)
            temp_file.flush()
            temp_file.close()
            self.file.close()
            self._local_file = open(temp_file.name, 'rU')

        self._local_file.seek(0)
        return self._local_file

    @property
    def data_rows(self):
        """Iterable of rows, made of iterable of column values of the raw data"""
        csv_reader = csv.reader(self.local_file)
        for row in csv_reader:
            yield row

    @property
    def cleaned_data_rows(self):
        """Iterable of rows, made of iterable of column values of cleaned data"""
        for row in self.data_rows:
            cleaned_row = []
            for tcm in self.tablecolumnmappings:
                val = u"%s" % row[tcm.order - 1]
                try:
                    if tcm.datacoercions.all().filter(source_string=val).count() > 0:
                        cleaned_row.append(
                            tcm.datacoercions.all().filter(source_string=val)[0].destination_value)
                    else:
                        cleaned_row.append(val)
                except:
                    print "problem with val: %s" % val
                    from traceback import print_exc
                    print_exc()
            yield cleaned_row

    def cache_first_rows(self):
        self.file.seek(0)

        counter = 0
        csv_reader = csv.reader(self.local_file)
        NUM_LINES_TO_CAPTURE = 6
        for row in csv_reader:
            counter += 1
            if counter <= NUM_LINES_TO_CAPTURE:
                if counter == 1:
                    self.cached_first_row = ROW_DELIMITER.join(row)
                    self.cached_second_to_fifth_row = ""
                else:
                    self.cached_second_to_fifth_row += "%s\n" % ROW_DELIMITER.join(row)

        self.num_rows = counter
        if self.has_header_row:
            self.num_rows = self.num_rows - 1
        self.num_columns = len(self.first_row_columns)

    @property
    def first_row_columns(self):
        if not hasattr(self, "_first_row_columns"):
            self._first_row_columns = self.cached_first_row.split(ROW_DELIMITER)
        return self._first_row_columns

    def save_cached_mapped_columns(self, columns):
        self.cached_mapped_columns = json.dumps(columns)
        self.save()

    @property
    def get_cached_mapped_columns(self):
        # create a list of tuples
        data = json.loads(self.cached_mapped_columns)
        result = []
        for d in data:
            result.append((d['to_table_name'], d['to_field']))

        return result

    @property
    def second_to_fifth_rows(self):
        if not hasattr(self, "_second_to_fifth_row"):
            if self.cached_second_to_fifth_row == "":
                self._second_to_fifth_row = []
            else:
                self._second_to_fifth_row = [r.split(ROW_DELIMITER) for r in
                                             self.cached_second_to_fifth_row.splitlines()]

        return self._second_to_fifth_row

    @property
    def tablecolumnmappings(self):
        return self.tablecolumnmapping_set.all().filter(active=True).order_by("order", ).distinct()

    @property
    def tablecolumnmappings_failed(self):
        return self.tablecolumnmappings.filter(
            Q(destination_field="") | Q(destination_field=None) | Q(destination_model="") | Q(
                destination_model=None)).exclude(ignored=True).filter(active=True).distinct()

    @property
    def num_failed_tablecolumnmappings(self):
        return self.tablecolumnmappings_failed.count()

    def tablecolumnmapping_formset(self, *args, **kwargs):
        from seed.data_importer import TableColumnMappingFormSet
        formset = TableColumnMappingFormSet(queryset=self.tablecolumnmappings)
        return formset

    @property
    def num_mapping_total(self):
        return self.tablecolumnmappings.count()

    @property
    def num_mapping_remaining(self):
        return self.num_mapping_errors or 0

    @property
    def num_mapping_complete(self):
        num = (self.num_mapping_total or self.num_mapping_remaining) - self.num_mapping_remaining
        if num < 0:
            num = 0
        return num

    @property
    def num_cleaning_total(self):
        return self.num_coercions_total or self.num_cleaning_remaining or 0

    @property
    def num_cleaning_remaining(self):
        return self.num_coercion_errors

    @property
    def num_cleaning_complete(self):
        num = self.num_cleaning_total - self.num_cleaning_remaining
        if num < 0:
            num = 0
        return num

    @property
    def filename_only(self):
        name = unquote(self.file.name)
        return name[name.rfind("/") + 1:name.rfind(".")]

    @property
    def filename(self):
        name = unquote(self.file.name)
        return name[name.rfind("/") + 1:len(name)]

    @property
    def ready_to_import(self):
        return self.num_coercion_errors == 0 and self.num_mapping_errors == 0  # and self.num_validation_errors == 0

    @property
    def num_cells(self):
        return self.num_rows * self.num_columns

    @property
    def tcm_json(self):
        # JSON used to render the mapping interface.
        tcms = []
        try:
            row_number = 0
            for tcm in self.tablecolumnmappings:
                row_number += 1
                error_message_text = ""
                if tcm.error_message_text:
                    error_message_text = tcm.error_message_text.replace("\n", "<br>")

                first_rows = ["", "", "", "", ""]
                if tcm.first_five_rows:
                    first_rows = ["%s" % r for r in tcm.first_five_rows]
                tcms.append({
                    'row_number': row_number,
                    'pk': tcm.pk,
                    'destination_model': tcm.destination_model,
                    'destination_field': tcm.destination_field,
                    'order': tcm.order,
                    'ignored': tcm.ignored,
                    'confidence': tcm.confidence,
                    'was_a_human_decision': tcm.was_a_human_decision,
                    'error_message_text': error_message_text,
                    'active': tcm.active,
                    'is_mapped': tcm.is_mapped,
                    'header_row': tcm.first_row,
                    'first_rows': first_rows,
                })
        except:
            from traceback import print_exc
            print_exc()

        return json.dumps(tcms)

    @property
    def tcm_errors_json(self):
        # JSON used to render the mapping interface.
        tcms = []
        try:
            row_number = 0
            for tcm in self.tablecolumnmappings:
                row_number += 1
                error_message_text = ""
                if tcm.error_message_text:
                    error_message_text = tcm.error_message_text.replace("\n", "<br>")

                tcms.append({
                    'row_number': row_number,
                    'pk': tcm.pk,
                    'order': tcm.order,
                    'is_mapped': tcm.is_mapped,
                    'error_message_text': error_message_text,
                })
        except:
            from traceback import print_exc
            print_exc()

        return json.dumps(tcms)

    @property
    def tcm_fields_to_save(self):
        t = TableColumnMapping()
        return t.fields_to_save

    @property
    def QUEUED_TCM_SAVE_COUNTER_KEY(self):
        return "QUEUED_TCM_SAVE_%s" % self.pk

    @property
    def QUEUED_TCM_DATA_KEY(self):
        return "QUEUED_TCM_DATA_KEY%s" % self.pk

    @property
    def UPDATING_TCMS_KEY(self):
        return "UPDATING_TCMS_KEY%s" % self.pk

    def update_tcms_from_save(self, json_data, save_counter):
        # Check save_counter vs queued_save_counters.
        queued_save_counter = get_cache_raw(self.QUEUED_TCM_SAVE_COUNTER_KEY, None)
        if not queued_save_counter or save_counter > queued_save_counter:
            if not get_cache_state(self.UPDATING_TCMS_KEY, None):
                set_cache_state(self.UPDATING_TCMS_KEY, True)
                for d in json.loads(json_data):

                    tcm = TableColumnMapping.objects.get(pk=d["pk"])
                    for field_name in TableColumnMapping.fields_to_save:
                        if not field_name == "pk":
                            setattr(tcm, field_name, d[field_name])
                    tcm.was_a_human_decision = True
                    tcm.save()

                if get_cache_raw(self.QUEUED_TCM_SAVE_COUNTER_KEY, False) is not False:
                    queued_data = get_cache_raw(self.QUEUED_TCM_DATA_KEY)
                    queued_time = get_cache_raw(self.QUEUED_TCM_SAVE_COUNTER_KEY)
                    delete_cache(self.QUEUED_TCM_DATA_KEY)
                    delete_cache(self.QUEUED_TCM_SAVE_COUNTER_KEY)
                    delete_cache(self.UPDATING_TCMS_KEY)
                    self.update_tcms_from_save(queued_data, queued_time)

                delete_cache(self.UPDATING_TCMS_KEY)
                delete_cache(self.QUEUED_TCM_DATA_KEY)
                delete_cache(self.QUEUED_TCM_SAVE_COUNTER_KEY)
                return True

            else:
                set_cache_raw(self.QUEUED_TCM_SAVE_COUNTER_KEY, save_counter)
                set_cache_raw(self.QUEUED_TCM_DATA_KEY, json_data)
        return False

    @property
    def CLEANING_PROGRESS_KEY(self):
        return "CLEANING_PROGRESS_KEY%s" % self.pk

    @property
    def cleaning_progress_pct(self):
        if not self.coercion_mapping_active and not self.coercion_mapping_queued and self.num_coercions_total > 0:
            return 100.0
        if self.coercion_mapping_active:
            return get_cache(self.CLEANING_PROGRESS_KEY)['progress']
        elif self.coercion_mapping_queued or not self.coercion_mapping_done:
            return 0.0
        else:
            return 100.0

    @classmethod
    def CLEANING_QUEUED_CACHE_KEY_GENERATOR(cls, pk):
        return "CLEANING_QUEUED_CACHE_KEY%s" % pk

    @property
    def CLEANING_QUEUED_CACHE_KEY(self):
        return self.__class__.CLEANING_QUEUED_CACHE_KEY_GENERATOR(self.pk)

    @classmethod
    def CLEANING_ACTIVE_CACHE_KEY_GENERATOR(cls, pk):
        return "CLEANING_ACTIVE_CACHE_KEY%s" % pk

    @property
    def CLEANING_ACTIVE_CACHE_KEY(self):
        return self.__class__.CLEANING_ACTIVE_CACHE_KEY_GENERATOR(self.pk)

    @property
    def coercion_mapping_active(self):
        return get_cache_state(self.CLEANING_ACTIVE_CACHE_KEY, False)

    @property
    def coercion_mapping_queued(self):
        return get_cache_state(self.CLEANING_QUEUED_CACHE_KEY, False)

    @property
    def SAVE_COUNTER_CACHE_KEY(self):
        return "SAVE_COUNTER_KEY%s" % self.pk

    @property
    def EXPORT_READY_CACHE_KEY(self):
        return "EXPORT_READY%s" % self.pk

    @property
    def EXPORT_PCT_COMPLETE_CACHE_KEY(self):
        return "EXPORT_PCT_COMPLETE%s" % self.pk

    @property
    def EXPORT_QUEUED_CACHE_KEY(self):
        return "EXPORT_QUEUED%s" % self.pk

    @property
    def export_ready(self):
        return get_cache_state(self.EXPORT_READY_CACHE_KEY,
                               True) and self.export_file is not None and self.export_file != ""

    @property
    def export_generation_pct_complete(self):
        return get_cache_state(self.EXPORT_PCT_COMPLETE_CACHE_KEY, False)

    @property
    def export_url(self):
        ns = self.import_record.app_namespace
        return reverse("%s:download_export" % ns, args=(self.pk,))

    @property
    def generate_url(self):
        ns = self.import_record.app_namespace
        return reverse("%s:prepare_export" % ns, args=(self.pk,))

    @property
    def merge_progress_url(self):
        return reverse("data_importer:merge_progress", args=(self.pk,))

    @property
    def premerge_progress_url(self):
        return reverse("data_importer:pre_merge_progress", args=(self.pk,))

    @property
    def force_restart_cleaning_url(self):
        return reverse("data_importer:force_restart_cleaning", args=(self.pk,))

    def find_unmatched_states(self, kls):
        """Get unmatched property states' id info from an import file.

        :rtype: list of tuples, field values specified in BS_VALUES_LIST.

        NJA: This function is a straight copy/update to find_unmatched_property_states
        """

        from seed.models import (
            PropertyState,
            TaxLotState,
            DATA_STATE_MAPPING
        )

        assert kls in [PropertyState, TaxLotState], \
            "Must be one of our State objects [PropertyState, TaxLotState]!"

        return kls.objects.filter(
            data_state__in=[DATA_STATE_MAPPING],
            import_file=self.id,
        )

    def find_unmatched_property_states(self):
        """Get unmatched property states' id info from an import file.

        # TODO - Fix Comment
        :rtype: list of tuples, field values specified in BS_VALUES_LIST.

        """

        from seed.models import PropertyState
        return self.find_unmatched_states(PropertyState)

    def find_unmatched_tax_lot_states(self):
        """Get unmatched property states' id info from an import file.

        # TODO - Fix Comment
        :rtype: list of tuples, field values specified in BS_VALUES_LIST.

        NB: This does not return a queryset!

        """

        from seed.models import TaxLotState
        return self.find_unmatched_states(TaxLotState)


class TableColumnMapping(models.Model):
    app = models.CharField(max_length=64, default='')
    source_string = models.TextField()
    import_file = models.ForeignKey(ImportFile)
    destination_model = models.CharField(max_length=255, blank=True, null=True)
    destination_field = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(blank=True, null=True)
    confidence = models.FloatField(default=0)
    ignored = models.BooleanField(default=False)
    was_a_human_decision = models.BooleanField(default=False)
    error_message_text = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    fields_to_save = ["pk", "destination_model", "destination_field", "ignored"]

    class Meta:
        ordering = ("order",)

    def __unicode__(self, *args, **kwargs):
        return "%s from %s -> %s (%s)" % (
            self.source_string, self.import_file, self.destination_model, self.destination_field,)

    def save(self, *args, **kwargs):
        if not self.app:
            self.app = self.import_file.import_record.app
        if self.ignored or not self.is_mapped:
            self.error_message_text = ""
        super(TableColumnMapping, self).save(*args, **kwargs)

    @property
    def source_string_sha(self):
        if not hasattr(self, "_source_string_sha"):
            m = hashlib.md5()
            m.update(self.source_string)
            self._source_string_sha = m.hexdigest()
        return self._source_string_sha

    @property
    def combined_model_and_field(self):
        return "%s.%s" % (self.destination_model, self.destination_field)

    @property
    def friendly_destination_model(self):
        return "%s" % (de_camel_case(self.destination_model),)

    @property
    def friendly_destination_field(self):
        return "%s" % (self.destination_field.replace("_", " ").replace("-", "").capitalize(),)

    @property
    def friendly_destination_model_and_field(self):
        if self.ignored:
            return "Ignored"
        elif self.destination_field and self.destination_model:
            return "%s: %s" % (self.friendly_destination_model, self.friendly_destination_field,)
        return "Unmapped"

    @property
    def datacoercions(self):
        return self.datacoercionmapping_set.all().filter(active=True)

    @property
    def datacoercion_errors(self):
        return self.datacoercionmapping_set.all().filter(active=True, valid_destination_value=False)

    @property
    def first_row(self):
        if not hasattr(self, "_first_row"):
            first_row = None
            try:
                first_row = self.import_file.first_row_columns[self.order - 1]
            except:
                pass

            self._first_row = first_row
        return self._first_row

    @property
    def first_five_rows(self):
        if not hasattr(self, "_first_five_rows"):
            first_rows = []
            for r in self.import_file.second_to_fifth_rows:
                try:
                    if r[self.order - 1]:
                        first_rows.append(r[self.order - 1])
                    else:
                        first_rows.append('')
                except:
                    first_rows.append('')
                    pass

            self._first_five_rows = first_rows

        return self._first_five_rows

    @property
    def destination_django_field(self):
        """commented out by AKL, not needed for SEED and removes dependency on
           libs.
        """
        # return find_field_named(self.destination_field, self.destination_model, get_class=True)
        return None

    @property
    def destination_django_field_has_choices(self):
        return self.destination_django_field.choices != []

    @property
    def destination_django_field_choices(self):
        try:
            return sorted(self.destination_django_field.choices, key=lambda choice: choice[1])
        except:
            return self.destination_django_field.choices

    @property
    def validation_rules(self):
        return self.validationrule_set.all()

    @property
    def is_mapped(self):
        return self.ignored or (
            self.destination_field is not None and self.destination_model is not None and self.destination_field != "" and self.destination_model != "")


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
        except:
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
        return "%s" % (self.building_record,)


def queue_update_status_for_import_record(pk):
    """edited by AKL to trim down data_importer"""
    # if not cache.get(ImportRecord.SUMMARY_ANALYSIS_ACTIVE_KEY(pk), False) and not cache.get(ImportRecord.SUMMARY_ANALYSIS_QUEUED_KEY(pk), False) and not "test" in sys.argv:
    return None


def update_status_from_import_record(sender, instance, **kwargs):
    try:
        queue_update_status_for_import_record(instance.pk)
    except ObjectDoesNotExist:
        pass


def update_status_from_import_file(sender, instance, **kwargs):
    try:
        queue_update_status_for_import_record(instance.import_record.pk)
    except ObjectDoesNotExist:
        pass


def update_status_from_tcm(sender, instance, **kwargs):
    try:
        queue_update_status_for_import_record(instance.import_file.import_record.pk)
    except ObjectDoesNotExist:
        pass


def update_status_from_dcm(sender, instance, **kwargs):
    try:
        queue_update_status_for_import_record(
            instance.table_column_mapping.import_file.import_record.pk)
    except ObjectDoesNotExist:
        pass


post_save.connect(update_status_from_import_record, sender=ImportRecord)
# post_save.connect(update_status_from_import_file, sender=ImportFile)
# post_save.connect(update_status_from_tcm, sender=TableColumnMapping)
# post_save.connect(update_status_from_dcm, sender=DataCoercionMapping)
