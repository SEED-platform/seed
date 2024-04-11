# !/usr/bin/env python
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import contextlib
import csv
import json
import locale
import logging
import tempfile
from urllib.parse import unquote

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django_extensions.db.models import TimeStampedModel

from config.utils import de_camel_case
from seed.data_importer.managers import NotDeletedManager
from seed.lib.mcm.reader import ROW_DELIMITER
from seed.lib.superperms.orgs.models import AccessLevelInstance
from seed.lib.superperms.orgs.models import Organization as SuperOrganization
from seed.utils.cache import delete_cache, get_cache, get_cache_raw, get_cache_state, set_cache_raw, set_cache_state

_log = logging.getLogger(__name__)

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


class DuplicateDataError(RuntimeError):
    def __init__(self, dup_id):
        super().__init__()
        self.id = dup_id


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
    # TODO: use these instead of the others defined in models.py
    IMPORT_STATUSES = [
        (STATUS_UPLOADING, 'Uploading'),
        (STATUS_MACHINE_MAPPING, 'Machine Mapping'),
        (STATUS_MAPPING, 'Needs Mapping'),
        (STATUS_MACHINE_CLEANING, 'Machine Cleaning'),
        (STATUS_CLEANING, 'Needs Cleaning'),
        (STATUS_READY_TO_PRE_MERGE, 'Ready to Merge'),
        (STATUS_PRE_MERGING, 'Merging'),
        (STATUS_READY_TO_MERGE, 'Merge Complete'),
        (STATUS_MERGING, 'Importing'),
        (STATUS_LIVE, 'Live'),
        (STATUS_UNKNOWN, 'Unknown'),
        (STATUS_MATCHING, 'Matching'),
    ]

    name = models.CharField(max_length=255, blank=True, null=True, verbose_name='Name Your Dataset',
                            default='Unnamed Dataset')
    app = models.CharField(
        max_length=64,
        blank=False,
        null=False,
        verbose_name='Destination App',
        help_text='The application (e.g., BPD or SEED) for this dataset',
        default='seed',
    )
    owner = models.ForeignKey('landing.SEEDUser', on_delete=models.CASCADE, blank=True, null=True)
    access_level_instance = models.ForeignKey(AccessLevelInstance, on_delete=models.CASCADE, null=False,
                                              related_name='import_record')
    start_time = models.DateTimeField(blank=True, null=True)
    finish_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)
    last_modified_by = models.ForeignKey(
        'landing.SEEDUser', on_delete=models.CASCADE, related_name='modified_import_records', blank=True, null=True
    )
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
    status = models.IntegerField(default=0, choices=IMPORT_STATUSES)
    super_organization = models.ForeignKey(
        SuperOrganization, on_delete=models.CASCADE, blank=True, null=True, related_name='import_records'
    )

    def __str__(self):
        return f'ImportRecord {self.pk}: {self.name}, started at {self.start_time}'

    class Meta:
        ordering = ('-updated_at',)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        for f in self.files:
            f.delete()

    @property
    def files(self):
        return self.importfile_set.all().order_by('file')

    @property
    def num_failed_tablecolumnmappings(self):
        if not hasattr(self, '_num_failed_tablecolumnmappings'):
            total = 0
            for f in self.files:
                total += f.num_failed_tablecolumnmappings
            self._num_failed_tablecolumnmappings = total
        return self._num_failed_tablecolumnmappings

    @property
    def num_coercion_errors(self):
        if not hasattr(self, '_num_failed_num_coercion_errors'):
            total = 0
            for f in self.files:
                total += f.num_coercion_errors

            self._num_failed_num_coercion_errors = total
        return self._num_failed_num_coercion_errors

    @property
    def num_validation_errors(self):
        if not hasattr(self, '_num_failed_validation_errors'):
            total = 0
            for f in self.files:
                total += f.num_validation_errors
            self._num_failed_validation_errors = total
        return self._num_failed_validation_errors

    @property
    def num_rows(self):
        if not hasattr(self, '_num_rows'):
            total = 0
            for f in self.files:
                total += f.num_rows
            self._num_rows = total
        return self._num_rows

    @property
    def num_columns(self):
        if not hasattr(self, '_num_columns'):
            total = 0
            for f in self.files:
                total += f.num_columns
            self._num_columns = total
        return self._num_columns


class ImportFile(NotDeletableModel, TimeStampedModel):
    import_record = models.ForeignKey(ImportRecord, on_delete=models.CASCADE)
    cycle = models.ForeignKey('seed.Cycle', on_delete=models.CASCADE, blank=True, null=True)
    file = models.FileField(upload_to='data_imports', max_length=500, blank=True, null=True)
    # Save the name of the raw file that was uploaded before it was saved to disk with the unique
    # extension.
    uploaded_filename = models.CharField(blank=True, max_length=255)
    file_size_in_bytes = models.IntegerField(blank=True, null=True)

    cached_first_row = models.TextField(blank=True, null=True)
    # Save a list of the final column mapping names that were used for this file.
    # This should really be a many-to-many with the column/ColumnMapping table.
    cached_mapped_columns = models.TextField(blank=True, null=True)
    cached_second_to_fifth_row = models.TextField(blank=True, null=True)
    has_header_row = models.BooleanField(default=True)
    has_generated_headers = models.BooleanField(default=False)
    mapping_completion = models.IntegerField(blank=True, null=True)
    mapping_done = models.BooleanField(default=False)
    mapping_error_messages = models.TextField(blank=True, null=True)
    matching_completion = models.IntegerField(blank=True, null=True)
    matching_done = models.BooleanField(default=False)
    matching_results_data = models.JSONField(default=dict, blank=True)
    multiple_cycle_upload = models.BooleanField(default=False)
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
    source_program = models.CharField(blank=True, max_length=80)
    # program version is in format 'x.y[.z]'
    source_program_version = models.CharField(blank=True, max_length=40)
    # Used by the BuildingSync import flow to link property states to file names (necessary for zip files)
    raw_property_state_to_filename = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = (
            '-modified',
            '-created',
        )

    def __str__(self):
        return '%s' % self.file.name

    def save(self, in_validation=False, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            if not in_validation:
                return None
        except ImportRecord.DoesNotExist:
            pass
            # If we're deleting.

    def __del__(self):
        if hasattr(self, '_local_file'):
            self._local_file.close()

    @property
    def from_portfolio_manager(self):
        return self._strcmp(self.source_program, 'PortfolioManager')

    @property
    def access_level_instance(self):
        return self.import_record.access_level_instance

    @property
    def from_buildingsync(self):
        source_type = self.source_type if self.source_type else ''
        return 'buildingsync' in source_type.lower()

    def _strcmp(self, a, b, ignore_ws=True, ignore_case=True):
        """Easily controlled loose string-matching."""
        if ignore_ws:
            a, b = a.strip(), b.strip()
        if ignore_case:
            a, b = a.lower(), b.lower()
        return a == b

    @property
    def local_file(self):
        """This method is used to create a copy of a remote file locally. We shouldn't need to use
        this unless we start storing files remotely and we need to save locally to parse. If that
        is the case, then we should handle the removal of the temp files otherwise these can add up
        to a lot of storage space.
        """
        if not hasattr(self, '_local_file'):
            temp_file = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
            for chunk in self.file.chunks(1024):
                temp_file.write(chunk)
            temp_file.flush()
            temp_file.close()
            self.file.close()
            self._local_file = open(temp_file.name, newline=None, encoding=locale.getpreferredencoding(False))  # noqa: SIM115

        self._local_file.seek(0)
        return self._local_file

    @property
    def data_rows(self):
        """Iterable of rows, made of iterable of column values of the raw data"""
        csv_reader = csv.reader(self.local_file)
        for row in csv_reader:
            try:
                yield row
            except StopIteration:
                return

    @property
    def cleaned_data_rows(self):
        """Iterable of rows, made of iterable of column values of cleaned data"""
        for row in self.data_rows:
            cleaned_row = []
            for tcm in self.tablecolumnmappings:
                val = '%s' % row[tcm.order - 1]
                try:
                    if tcm.datacoercions.all().filter(source_string=val).count() > 0:
                        cleaned_row.append(tcm.datacoercions.all().filter(source_string=val)[0].destination_value)
                    else:
                        cleaned_row.append(val)
                except BaseException:
                    _log.error(f'problem with val: {val}')
                    from traceback import print_exc

                    print_exc()
            try:
                yield cleaned_row
            except StopIteration:
                return

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
                    self.cached_second_to_fifth_row = ''
                else:
                    self.cached_second_to_fifth_row += '%s\n' % ROW_DELIMITER.join(row)

        self.num_rows = counter
        if self.has_header_row:
            self.num_rows = self.num_rows - 1
        self.num_columns = len(self.first_row_columns)

    @property
    def first_row_columns(self):
        if not hasattr(self, '_first_row_columns'):
            if self.cached_first_row:
                self._first_row_columns = self.cached_first_row.split(ROW_DELIMITER)
                _log.debug('Using cached first row columns.')
            else:
                _log.debug('No first row columns property or cache was found!')
                return None
        return self._first_row_columns

    def save_cached_mapped_columns(self, columns):
        self.cached_mapped_columns = json.dumps(columns)
        self.save()

    @property
    def get_cached_mapped_columns(self):
        # create a list of tuples
        data = json.loads(self.cached_mapped_columns or '{}')
        result = []
        for d in data:
            result.append((d['to_table_name'], d['to_field']))

        return result

    @property
    def second_to_fifth_rows(self):
        if not hasattr(self, '_second_to_fifth_row'):
            if self.cached_second_to_fifth_row == '':
                self._second_to_fifth_row = []
            else:
                self._second_to_fifth_row = [r.split(ROW_DELIMITER) for r in
                                             self.cached_second_to_fifth_row.splitlines()]

        return self._second_to_fifth_row

    @property
    def tablecolumnmappings(self):
        return (
            self.tablecolumnmapping_set.all()
            .filter(active=True)
            .order_by(
                'order',
            )
            .distinct()
        )

    @property
    def tablecolumnmappings_failed(self):
        return (
            self.tablecolumnmappings.filter(
                Q(destination_field='') | Q(destination_field=None) | Q(destination_model='') | Q(
                    destination_model=None)
            )
            .exclude(ignored=True)
            .filter(active=True)
            .distinct()
        )

    @property
    def num_failed_tablecolumnmappings(self):
        return self.tablecolumnmappings_failed.count()

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
        return name[name.rfind('/') + 1: name.rfind('.')]

    @property
    def filename(self):
        name = unquote(self.file.name)
        return name[name.rfind('/') + 1: len(name)]

    @property
    def ready_to_import(self):
        return self.num_coercion_errors == 0 and self.num_mapping_errors == 0  # and self.num_validation_errors == 0

    @property
    def num_cells(self):
        return self.num_rows * self.num_columns

    @property
    def tcm_errors_json(self):
        # JSON used to render the mapping interface.
        tcms = []
        try:
            for row_number, tcm in enumerate(self.tablecolumnmappings, start=1):
                error_message_text = ''
                if tcm.error_message_text:
                    error_message_text = tcm.error_message_text.replace('\n', '<br>')

                tcms.append(
                    {
                        'row_number': row_number,
                        'pk': tcm.pk,
                        'order': tcm.order,
                        'is_mapped': tcm.is_mapped,
                        'error_message_text': error_message_text,
                    }
                )
        except BaseException:
            from traceback import print_exc

            print_exc()

        return json.dumps(tcms)

    @property
    def tcm_fields_to_save(self):
        t = TableColumnMapping()
        return t.fields_to_save

    @property
    def queued_tcm_save_counter_key(self):
        return f'QUEUED_TCM_SAVE_{self.pk}'

    @property
    def queued_tcm_data_key(self):
        return f'queued_tcm_data_key{self.pk}'

    @property
    def updating_tcms_key(self):
        return f'updating_tcms_key{self.pk}'

    def update_tcms_from_save(self, json_data, save_counter):
        # Check save_counter vs queued_save_counters.
        queued_save_counter = get_cache_raw(self.queued_tcm_save_counter_key, None)
        if not queued_save_counter or save_counter > queued_save_counter:
            if not get_cache_state(self.updating_tcms_key, None):
                set_cache_state(self.updating_tcms_key, True)
                for d in json.loads(json_data):
                    tcm = TableColumnMapping.objects.get(pk=d['pk'])
                    for field_name in TableColumnMapping.fields_to_save:
                        if field_name != 'pk':
                            setattr(tcm, field_name, d[field_name])
                    tcm.was_a_human_decision = True
                    tcm.save()

                if get_cache_raw(self.queued_tcm_save_counter_key, False) is not False:
                    queued_data = get_cache_raw(self.queued_tcm_data_key)
                    queued_time = get_cache_raw(self.queued_tcm_save_counter_key)
                    delete_cache(self.queued_tcm_data_key)
                    delete_cache(self.queued_tcm_save_counter_key)
                    delete_cache(self.updating_tcms_key)
                    self.update_tcms_from_save(queued_data, queued_time)

                delete_cache(self.updating_tcms_key)
                delete_cache(self.queued_tcm_data_key)
                delete_cache(self.queued_tcm_save_counter_key)
                return True

            else:
                set_cache_raw(self.queued_tcm_save_counter_key, save_counter)
                set_cache_raw(self.queued_tcm_data_key, json_data)
        return False

    @property
    def cleaning_progress_key(self):
        return f'cleaning_progress_key{self.pk}'

    @property
    def cleaning_progress_pct(self):
        if not self.coercion_mapping_active and not self.coercion_mapping_queued and self.num_coercions_total > 0:
            return 100.0
        if self.coercion_mapping_active:
            return get_cache(self.cleaning_progress_key)['progress']
        elif self.coercion_mapping_queued or not self.coercion_mapping_done:
            return 0.0
        else:
            return 100.0

    @classmethod
    def cleaning_queued_cache_key_generator(cls, pk):
        return f'CLEANING_QUEUED_CACHE_KEY{pk}'

    @property
    def cleaning_queued_cache_key(self):
        return self.__class__.cleaning_queued_cache_key_generator(self.pk)

    @classmethod
    def cleaning_active_cache_key_generator(cls, pk):
        return f'CLEANING_ACTIVE_CACHE_KEY{pk}'

    @property
    def cleaning_active_cache_key(self):
        return self.__class__.cleaning_active_cache_key_generator(self.pk)

    @property
    def coercion_mapping_active(self):
        return get_cache_state(self.cleaning_active_cache_key, False)

    @property
    def coercion_mapping_queued(self):
        return get_cache_state(self.cleaning_queued_cache_key, False)

    @property
    def force_restart_cleaning_url(self):
        return reverse('data_importer:force_restart_cleaning', args=(self.pk,))

    def find_unmatched_states(self, kls):
        """Get unmatched property states' id info from an import file.

        :return: QuerySet, list of model objects [either PropertyState or TaxLotState]
        """

        from seed.models import DATA_STATE_MAPPING, PropertyState, TaxLotState

        if kls not in {PropertyState, TaxLotState}:
            raise ValueError('Must be one of our State objects [PropertyState, TaxLotState]!')

        return kls.objects.filter(
            data_state__in=[DATA_STATE_MAPPING],
            import_file=self.id,
        )

    def find_unmatched_property_states(self):
        """Get unmatched property states' id info from an import file.

        :return: QuerySet, list of PropertyState objects
        """

        from seed.models import PropertyState

        return self.find_unmatched_states(PropertyState)

    def find_unmatched_tax_lot_states(self):
        """Get unmatched property states' id info from an import file.

        :return: QuerySet, list of TaxLotState objects
        """

        from seed.models import TaxLotState

        return self.find_unmatched_states(TaxLotState)


class TableColumnMapping(models.Model):
    app = models.CharField(max_length=64, default='')
    source_string = models.TextField()
    import_file = models.ForeignKey(ImportFile, on_delete=models.CASCADE)
    destination_model = models.CharField(max_length=255, blank=True, null=True)
    destination_field = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(blank=True, null=True)
    confidence = models.FloatField(default=0)
    ignored = models.BooleanField(default=False)
    was_a_human_decision = models.BooleanField(default=False)
    error_message_text = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    fields_to_save = ['pk', 'destination_model', 'destination_field', 'ignored']

    class Meta:
        ordering = ('order',)

    def __str__(self, *args, **kwargs):
        return f'{self.source_string} from {self.import_file} -> {self.destination_model} ({self.destination_field})'

    def save(self, *args, **kwargs):
        if not self.app:
            self.app = self.import_file.import_record.app
        if self.ignored or not self.is_mapped:
            self.error_message_text = ''
        super().save(*args, **kwargs)

    @property
    def combined_model_and_field(self):
        return f'{self.destination_model}.{self.destination_field}'

    @property
    def friendly_destination_model(self):
        return de_camel_case(self.destination_model)

    @property
    def friendly_destination_field(self):
        return self.destination_field.replace("_", " ").replace("-", "").capitalize()

    @property
    def friendly_destination_model_and_field(self):
        if self.ignored:
            return 'Ignored'
        elif self.destination_field and self.destination_model:
            return f'{self.friendly_destination_model}: {self.friendly_destination_field}'
        return 'Unmapped'

    @property
    def datacoercions(self):
        return self.datacoercionmapping_set.all().filter(active=True)

    @property
    def datacoercion_errors(self):
        return self.datacoercionmapping_set.all().filter(active=True, valid_destination_value=False)

    @property
    def first_row(self):
        if not hasattr(self, '_first_row'):
            with contextlib.suppress(BaseException):
                first_row = self.import_file.first_row_columns[self.order - 1]

            self._first_row = first_row
        return self._first_row

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
        except BaseException:
            return self.destination_django_field.choices

    @property
    def validation_rules(self):
        return self.validationrule_set.all()

    @property
    def is_mapped(self):
        return self.ignored or (
            self.destination_field is not None
            and self.destination_model is not None
            and self.destination_field != ''
            and self.destination_model != ''
        )
