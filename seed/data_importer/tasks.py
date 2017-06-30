# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import

import collections
import copy
import hashlib
import operator
import time
import traceback
import datetime
from _csv import Error
from collections import namedtuple
from functools import reduce
from itertools import chain
from random import randint

from celery import chord
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from unidecode import unidecode

from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
    STATUS_READY_TO_MERGE,
)
from seed.decorators import get_prog_key
from seed.decorators import lock_and_track
from seed.green_button import xml_importer
from seed.lib.mappings.mapping_data import MappingData
from seed.lib.mcm import cleaners, mapper, reader
from seed.lib.mcm.mapper import expand_rows
from seed.lib.mcm.utils import batch
from seed.lib.merging import merging
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    ASSESSED_BS,
    ASSESSED_RAW,
    GREEN_BUTTON_RAW,
    PORTFOLIO_BS,
    PORTFOLIO_RAW,
    Column,
    ColumnMapping,
    PropertyState,
    PropertyView,
    TaxLotView,
    TaxLotState,
    DATA_STATE_IMPORT,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    DATA_STATE_DELETE,
    MERGE_STATE_MERGED,
    MERGE_STATE_NEW,
    DATA_STATE_UNKNOWN)
from seed.models import PropertyAuditLog
from seed.models import TaxLotAuditLog
from seed.models import TaxLotProperty
from seed.models.auditlog import AUDIT_IMPORT
from seed.models.data_quality import DataQualityCheck
from seed.utils.buildings import get_source_type
from seed.utils.cache import set_cache, increment_cache, get_cache, delete_cache, get_cache_raw

_log = get_task_logger(__name__)

STR_TO_CLASS = {'TaxLotState': TaxLotState, 'PropertyState': PropertyState}


def get_cache_increment_value(chunk):
    denom = len(chunk) or 1
    return 1.0 / denom * 100


@shared_task
def check_data_chunk(model, ids, identifier, increment):
    """

    :param model: one of 'PropertyState' or 'TaxLotState'
    :param ids: list of primary key ids to process
    :param file_pk: import file primary key
    :param increment: currently unused, but needed because of the special method that appends this onto the function  # NOQA
    :return: None
    """
    if model == 'PropertyState':
        qs = PropertyState.objects.filter(id__in=ids)
    elif model == 'TaxLotState':
        qs = TaxLotState.objects.filter(id__in=ids)
    else:
        qs = None
    super_org = qs.first().organization

    d = DataQualityCheck.retrieve(super_org.get_parent())
    d.check_data(model, qs.iterator())
    d.save_to_cache(identifier)


@shared_task
def finish_checking(identifier):
    """
    Chord that is called after the data quality check is complete

    :param identifier: import file primary key
    :return:
    """

    prog_key = get_prog_key('check_data', identifier)
    data_quality_results = get_cache_raw(DataQualityCheck.cache_key(identifier))
    result = {
        'status': 'success',
        'progress': 100,
        'message': 'data quality check complete',
        'data': data_quality_results
    }
    set_cache(prog_key, result['status'], result)


@shared_task
def do_checks(propertystate_ids, taxlotstate_ids):
    identifier = randint(100, 100000)
    DataQualityCheck.initialize_cache(identifier)
    prog_key = get_prog_key('check_data', identifier)
    trigger_data_quality_checks.delay(propertystate_ids, taxlotstate_ids, identifier)
    return {'status': 'success', 'progress_key': prog_key}


@shared_task
def trigger_data_quality_checks(qs, tlqs, identifier):
    prog_key = get_prog_key('map_data', identifier)
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)

    # now call data_quality
    _data_quality_check(qs, tlqs, identifier)


@shared_task
def finish_import_record(import_record_pk):
    """Set all statuses to Done, etc."""
    states = ('done', 'active', 'queued')
    actions = ('merge_analysis', 'premerge_analysis')
    # Really all these status attributes are tedious.
    import_record = ImportRecord.objects.get(pk=import_record_pk)
    for action in actions:
        for state in states:
            value = False
            if state == 'done':
                value = True
            setattr(import_record, '{0}_{1}'.format(action, state), value)

    import_record.finish_time = timezone.now()
    import_record.status = STATUS_READY_TO_MERGE
    import_record.save()


@shared_task
def finish_mapping(import_file_id, mark_as_done):
    import_file = ImportFile.objects.get(pk=import_file_id)

    # Do not set the mapping_done flag unless mark_as_done is set. This allows an actual
    # user to review the mapping before it is saved and matching starts.
    if mark_as_done:
        import_file.mapping_done = True
        import_file.save()

    finish_import_record(import_file.import_record.pk)
    prog_key = get_prog_key('map_data', import_file_id)
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)

    property_state_ids = list(PropertyState.objects.filter(import_file=import_file)
                              .exclude(data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT, DATA_STATE_DELETE])
                              .values_list('id', flat=True))
    taxlot_state_ids = list(TaxLotState.objects.filter(import_file=import_file)
                            .exclude(data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT, DATA_STATE_DELETE])
                            .values_list('id', flat=True))

    # now call data_quality
    _data_quality_check(property_state_ids, taxlot_state_ids, import_file_id)


def _translate_unit_to_type(unit):
    if unit is None or unit == 'String':
        return 'string'

    return unit.lower()


def _build_cleaner(org):
    """Return a cleaner instance that knows about a mapping's unit types.

    Basically, this just tells us how to try and cast types during cleaning
    based on the Column definition in the database.

    :param org: organization instance.
    :returns: dict of dicts. {'types': {'col_name': 'type'},}
    """
    units = {'types': {}}
    for column in Column.objects.filter(mapped_mappings__super_organization=org).select_related(
            'unit'):
        column_type = 'string'
        if column.unit:
            column_type = _translate_unit_to_type(
                column.unit.get_unit_type_display()
            )
        units['types'][column.column_name] = column_type

    # Update with our predefined types for our database column types.
    units['types'].update(Column.retrieve_db_types()['types'])

    return cleaners.Cleaner(units)


@shared_task
def map_row_chunk(ids, file_pk, source_type, prog_key, increment, **kwargs):
    """Does the work of matching a mapping to a source type and saving

    :param ids: list of PropertyState IDs to map.
    :param file_pk: int, the PK for an ImportFile obj.
    :param source_type: int, represented by either ASSESSED_RAW or PORTFOLIO_RAW.
    :param prog_key: string, key of the progress key
    :param increment: double, value by which to increment progress key
    """

    _log.debug('Mapping row chunks')
    import_file = ImportFile.objects.get(pk=file_pk)
    save_type = PORTFOLIO_BS
    if source_type == ASSESSED_RAW:
        save_type = ASSESSED_BS

    org = Organization.objects.get(pk=import_file.import_record.super_organization.pk)

    # get all the table_mappings that exist for the organization
    table_mappings = ColumnMapping.get_column_mappings_by_table_name(org)

    # Remove any of the mappings that are not in the current list of raw columns because this
    # can really mess up the mapping of delimited_fields.
    # Ideally the table_mapping method would be attached to the import_file_id, someday...
    list_of_raw_columns = import_file.first_row_columns
    if list_of_raw_columns:
        for k, v in table_mappings.items():
            for key2 in v.keys():
                if key2 not in list_of_raw_columns:
                    del table_mappings[k][key2]

        # check that the dictionaries are not empty, if empty, then delete.
        for k in table_mappings.keys():
            if not table_mappings[k]:
                del table_mappings[k]

    # TODO: **START TOTAL TERRIBLE HACK**
    # For some reason the mappings that got created previously don't
    # always have the table class in them.  To get this working for
    # the demo this is an infix place, but is absolutely terrible and
    # should be removed ASAP!!!!!
    # NL: 4/12/2017, this should no longer be a problem after the column cleanup, remove and test post 2.0.2.
    if 'PropertyState' not in table_mappings and 'TaxLotState' in table_mappings and '' in table_mappings:
        _log.error('this code should not be running here...')
        debug_inferred_prop_state_mapping = table_mappings['']
        table_mappings['PropertyState'] = debug_inferred_prop_state_mapping
    # TODO: *END TOTAL TERRIBLE HACK**

    map_cleaner = _build_cleaner(org)

    # *** BREAK OUT INTO SEPARATE METHOD ***
    # figure out which import field is defined as the unique field that may have a delimiter of
    # individual values (e.g. tax lot ids). The definition of the delimited field is currently
    # hard coded
    try:
        delimited_fields = {}
        if 'TaxLotState' in table_mappings.keys():
            tmp = table_mappings['TaxLotState'].keys()[table_mappings['TaxLotState'].values().index(
                ('TaxLotState', 'jurisdiction_tax_lot_id'))]
            delimited_fields['jurisdiction_tax_lot_id'] = {
                'from_field': tmp,
                'to_table': 'TaxLotState',
                'to_field_name': 'jurisdiction_tax_lot_id',
            }
    except ValueError:
        delimited_fields = {}
        # field does not exist in mapping list, so ignoring

    # _log.debug("my table mappings are {}".format(table_mappings))
    _log.debug("delimited_field that will be expanded and normalized: {}".format(delimited_fields))

    # If a single file is being imported into both the tax lot and property table, then add
    # an extra custom mapping for the cross-related data. If the data are not being imported into
    # the property table then make sure to skip this so that superfluous property entries are
    # not created.
    if 'PropertyState' in table_mappings.keys():
        if delimited_fields and delimited_fields['jurisdiction_tax_lot_id']:
            table_mappings['PropertyState'][
                delimited_fields['jurisdiction_tax_lot_id']['from_field']] = (
                'PropertyState', 'lot_number')
    # *** END BREAK OUT ***

    # yes, there are three cascading for loops here. sorry :(
    md = MappingData()
    for table, mappings in table_mappings.iteritems():
        if not table:
            continue

        # This may be historic, but we need to pull out the extra_data_fields here to pass into
        # mapper.map_row. apply_columns are extra_data columns (the raw column names)
        extra_data_fields = []
        for k, v in mappings.iteritems():
            if not md.find_column(v[0], v[1]):
                extra_data_fields.append(k)
        _log.debug("extra data fields: {}".format(extra_data_fields))

        # All the data live in the PropertyState.extra_data field when the data are imported
        data = PropertyState.objects.filter(id__in=ids).only('extra_data').iterator()

        # Since we are importing CSV, then each extra_data field will have the same fields. So
        # save the map_model_obj outside of for loop to pass into the `save_column_names` methods
        map_model_obj = None

        # Loop over all the rows
        for original_row in data:

            # expand the row into multiple rows if needed with the delimited_field replaced with a
            # single value. This minimizes the need to rewrite the downstream code.
            expand_row = False
            for k, d in delimited_fields.iteritems():
                if d['to_table'] == table:
                    expand_row = True
            # _log.debug("Expand row is set to {}".format(expand_row))

            delimited_field_list = []
            for _, v in delimited_fields.iteritems():
                delimited_field_list.append(v['from_field'])

            # _log.debug("delimited_field_list is set to {}".format(delimited_field_list))

            # Weeee... the data are in the extra_data column.
            for row in expand_rows(original_row.extra_data, delimited_field_list, expand_row):
                map_model_obj = mapper.map_row(
                    row,
                    mappings,
                    STR_TO_CLASS[table],
                    extra_data_fields,
                    cleaner=map_cleaner,
                    **kwargs
                )

                # save cross related data, that is data that needs to go into the other model's
                # collection as well.

                # Assign some other arguments here
                map_model_obj.import_file = import_file
                map_model_obj.source_type = save_type
                map_model_obj.organization = import_file.import_record.super_organization
                if hasattr(map_model_obj, 'data_state'):
                    map_model_obj.data_state = DATA_STATE_MAPPING
                if hasattr(map_model_obj, 'organization'):
                    map_model_obj.organization = import_file.import_record.super_organization
                if hasattr(map_model_obj, 'clean'):
                    map_model_obj.clean()

                # There is a potential thread safe issue here:
                # This method is called in parallel on production systems, so we need to make
                # sure that the object hasn't already been created.
                # For example, in the test data the tax lot id is the same for many rows. Make sure
                # to only create/save the object if it hasn't been created before.
                if hash_state_object(map_model_obj, include_extra_data=False) == hash_state_object(
                        STR_TO_CLASS[table](organization=map_model_obj.organization),
                        include_extra_data=False):
                    # Skip this object as it has no data...
                    continue

                try:
                    # There was an error with a field being too long [> 255 chars].
                    map_model_obj.save()

                    # Create an audit log record for the new map_model_obj that was created.

                    AuditLogClass = PropertyAuditLog if isinstance(map_model_obj,
                                                                   PropertyState) else TaxLotAuditLog
                    AuditLogClass.objects.create(organization=org,
                                                 state=map_model_obj,
                                                 name='Import Creation',
                                                 description='Creation from Import file.',
                                                 import_filename=import_file,
                                                 record_type=AUDIT_IMPORT)

                except Exception as e:
                    # Could not save the record for some reason, raise an exception
                    raise Exception(
                        "Unable to save row the model with row {}:{}".format(type(e), e.message))

        # Make sure that we've saved all of the extra_data column names from the first item in list
        if map_model_obj:
            Column.save_column_names(map_model_obj)

    increment_cache(prog_key, increment)


@shared_task
@lock_and_track
def _map_data(import_file_id, mark_as_done):
    """
    Get all of the raw data and process it using appropriate mapping.
    @lock_and_track returns a progress_key

    :param import_file_id: int, the id of the import_file we're working with.
    :param mark_as_done: bool, tell finish_mapping that import_file.mapping_done is True
    :return:
    """
    _log.debug("Starting to map the data")
    prog_key = get_prog_key('map_data', import_file_id)
    import_file = ImportFile.objects.get(pk=import_file_id)

    # If we haven't finished saving, we should not proceed with mapping
    # Re-queue this task.
    if not import_file.raw_save_done:
        _log.debug("_map_data raw_save_done is false, queueing the task until raw_save finishes")
        map_data.apply_async(args=[import_file_id], countdown=60, expires=120)
        return {
            'status': 'error',
            'message': 'waiting for raw data save.',
            'progress_key': prog_key
        }

    source_type_dict = {
        'Portfolio Raw': PORTFOLIO_RAW,
        'Assessed Raw': ASSESSED_RAW,
        'Green Button Raw': GREEN_BUTTON_RAW,
    }
    source_type = source_type_dict.get(import_file.source_type, ASSESSED_RAW)

    qs = PropertyState.objects.filter(
        import_file=import_file,
        source_type=source_type,
        data_state=DATA_STATE_IMPORT,
    ).only('id').iterator()

    id_chunks = [[obj.id for obj in chunk] for chunk in batch(qs, 100)]
    increment = get_cache_increment_value(id_chunks)
    tasks = [map_row_chunk.s(ids, import_file_id, source_type, prog_key, increment)
             for ids in id_chunks]

    if tasks:
        # specify the chord as an immutable with .si
        chord(tasks, interval=15)(finish_mapping.si(import_file_id, mark_as_done))
    else:
        _log.debug("Not creating finish_mapping chord, calling directly")
        finish_mapping.si(import_file_id, mark_as_done)


@shared_task
@lock_and_track
def _data_quality_check(property_state_ids, taxlot_state_ids, identifier):
    """

    Get the mapped data and run the data_quality class against it in chunks. The
    mapped data are pulled from the PropertyState(or Taxlot) table.

    @lock_and_track returns a progress_key

    :param import_file_id: int, the id of the import_file we're working with.
    """
    # initialize the cache for the data_quality results using the data_quality static method
    tasks = []
    id_chunks = [[obj for obj in chunk] for chunk in batch(property_state_ids, 100)]
    increment = get_cache_increment_value(id_chunks)
    for ids in id_chunks:
        tasks.append(check_data_chunk.s("PropertyState", ids, identifier, increment))

    id_chunks_tl = [[obj for obj in chunk] for chunk in batch(taxlot_state_ids, 100)]
    increment_tl = get_cache_increment_value(id_chunks_tl)
    for ids in id_chunks_tl:
        tasks.append(check_data_chunk.s("TaxLotState", ids, identifier, increment_tl))

    if tasks:
        # specify the chord as an immutable with .si
        chord(tasks, interval=15)(finish_checking.si(identifier))
    else:
        finish_checking.s(identifier)
    prog_key = get_prog_key('check_data', identifier)
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    return result


@shared_task
def map_data(import_file_id, remap=False, mark_as_done=True):
    """
    Map data task. By default this method will run through the mapping and mark it as complete.
    :param import_file_id: Import File ID
    :param remap: bool, if remapping, then delete previous objects from the database
    :param mark_as_done: bool, if skip review then the mapping_done flag will be set to true at the
    end.
    :return: JSON
    """
    DataQualityCheck.initialize_cache(import_file_id)
    prog_key = get_prog_key('check_data', import_file_id)
    import_file = ImportFile.objects.get(pk=import_file_id)
    if remap:
        # Check to ensure that import files has not already been matched/merged.
        if import_file.matching_done or import_file.matching_completion:
            result = {
                'status': 'warning',
                'progress': 100,
                'message': 'Mapped buildings already merged',
            }
            return result

        # Delete properties already mapped for this file.
        PropertyState.objects.filter(
            import_file=import_file,
            data_state=DATA_STATE_MAPPING,
        ).delete()

        # Delete properties already mapped for this file.
        TaxLotState.objects.filter(
            import_file=import_file,
            data_state=DATA_STATE_MAPPING,
        ).delete()

        # Reset various flags
        import_file.mapping_done = False
        import_file.mapping_completion = None
        import_file.save()

    # delete the prog key -- in case it exists
    prog_key = get_prog_key('map_data', import_file_id)
    delete_cache(prog_key)
    _map_data.delay(import_file_id, mark_as_done)
    return {'status': 'success', 'progress_key': prog_key}


@shared_task
def _save_raw_data_chunk(chunk, file_pk, prog_key, increment):
    """
    Save the raw data to the database

    :param chunk: list, ids to process
    :param file_pk: ImportFile Primary Key
    :param prog_key: string, Progress Key to append progress
    :param increment: Float, Value by which to increment the progress
    :return: Bool, Always true
    """

    import_file = ImportFile.objects.get(pk=file_pk)

    # Save our "column headers" and sample rows for F/E.
    source_type = get_source_type(import_file)
    for c in chunk:
        raw_property = PropertyState(organization=import_file.import_record.super_organization)
        raw_property.import_file = import_file

        # sanitize c and remove any diacritics
        new_chunk = {}
        for k, v in c.iteritems():
            # remove extra spaces surrounding keys.
            key = k.strip()
            if isinstance(v, unicode):
                new_chunk[key] = unidecode(v)
            elif isinstance(v, (datetime.datetime, datetime.date)):
                raise TypeError("Datetime class not supported in Extra Data. Needs to be a string.")
            else:
                new_chunk[key] = v
        raw_property.extra_data = new_chunk
        raw_property.source_type = source_type  # not defined in new data model
        raw_property.data_state = DATA_STATE_IMPORT

        # We require a save to get our PK
        # We save here to set our initial source PKs.
        raw_property.save()

        super_org = import_file.import_record.super_organization
        raw_property.organization = super_org

        raw_property.save()

    # Indicate progress
    increment_cache(prog_key, increment)
    _log.debug('Returning from _save_raw_data_chunk')

    return True


@shared_task
def finish_raw_save(file_pk):
    """
    Finish importing the raw file.

    :param file_pk: ID of the file that was being imported
    :return: results: results from the other tasks before the chord ran
    """
    import_file = ImportFile.objects.get(pk=file_pk)
    import_file.raw_save_done = True
    import_file.save()
    prog_key = get_prog_key('save_raw_data', file_pk)
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)
    _log.debug('Returning from finish_raw_save')
    return result


def cache_first_rows(import_file, parser):
    """Cache headers, and rows 2-6 for validation/viewing.

    :param import_file: ImportFile inst.
    :param parser: MCMParser instance.
    """

    # return the first row of the headers which are cleaned
    first_row = parser.headers
    first_five_rows = parser.first_five_rows

    _log.debug(first_five_rows)

    import_file.cached_second_to_fifth_row = "\n".join(first_five_rows)
    if first_row:
        first_row = reader.ROW_DELIMITER.join(first_row)
    import_file.cached_first_row = first_row or ''
    import_file.save()


@shared_task
@lock_and_track
def _save_raw_green_button_data(file_pk):
    """
    Pulls identifying information out of the XML data, find_or_creates
    a building_snapshot for the data, parses and stores the time series
    meter data and associates it with the building snapshot.
    """

    import_file = ImportFile.objects.get(pk=file_pk)

    import_file.raw_save_done = True
    import_file.save()

    res = xml_importer.import_xml(import_file)

    prog_key = get_prog_key('save_raw_data', file_pk)
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)

    if res:
        return {
            'status': 'success',
            'progress': 100,
            'progress_key': prog_key
        }

    return {
        'status': 'error',
        'message': 'data failed to import',
        'progress_key': prog_key
    }


@shared_task
@lock_and_track
def _save_raw_data(file_pk, *args, **kwargs):
    """
    Worker method for saving raw data

    :param file_pk:
    :return: Dict, result from Progress Cache
    """

    """Chunk up the CSV or XLSX file and save the raw data into the DB PropertyState table."""
    prog_key = get_prog_key('save_raw_data', file_pk)
    _log.debug("Current cache state")
    current_cache = get_cache(prog_key)
    _log.debug(current_cache)
    time.sleep(2)  # NL: yuck
    result = current_cache

    try:
        _log.debug('Attempting to access import_file')
        import_file = ImportFile.objects.get(pk=file_pk)
        if import_file.raw_save_done:
            result['status'] = 'warning'
            result['message'] = 'Raw data already saved'
            result['progress'] = 100
            set_cache(prog_key, result['status'], result)
            _log.debug('Returning with warn from _save_raw_data')
            return result

        if import_file.source_type == "Green Button Raw":
            return _save_raw_green_button_data(file_pk)

        parser = reader.MCMParser(import_file.local_file)
        cache_first_rows(import_file, parser)
        rows = parser.next()
        import_file.num_rows = 0
        import_file.num_columns = parser.num_columns()

        chunks = []
        for batch_chunk in batch(rows, 100):
            import_file.num_rows += len(batch_chunk)
            chunks.append(batch_chunk)
        increment = get_cache_increment_value(chunks)
        tasks = [_save_raw_data_chunk.s(chunk, file_pk, prog_key, increment)
                 for chunk in chunks]

        _log.debug('Appended all tasks')
        import_file.save()
        _log.debug('Saved import_file')

        if tasks:
            _log.debug('Adding chord to queue')
            chord(tasks, interval=15)(finish_raw_save.si(file_pk))
        else:
            _log.debug('Skipped chord')
            finish_raw_save.s(file_pk)

        _log.debug('Finished raw save tasks')
        result = get_cache(prog_key)
    except StopIteration:
        result['status'] = 'error'
        result['message'] = 'StopIteration Exception'
        result['stacktrace'] = traceback.format_exc()
    except Error as e:
        result['status'] = 'error'
        result['message'] = 'File Content Error: ' + e.message
        result['stacktrace'] = traceback.format_exc()
    except KeyError as e:
        result['status'] = 'error'
        result['message'] = 'Invalid Column Name: "' + e.message + '"'
        result['stacktrace'] = traceback.format_exc()
    except Exception as e:
        result['status'] = 'error'
        result['message'] = 'Unhandled Error: ' + str(e.message)
        result['stacktrace'] = traceback.format_exc()

    set_cache(prog_key, result['status'], result)
    _log.debug('Returning from end of _save_raw_data with state:')
    _log.debug(result)
    return result


@shared_task
@lock_and_track
def save_raw_data(file_pk, *args, **kwargs):
    """
    Save the raw data from an imported file. This is the entry point into saving the data.

    :param file_pk: ImportFile Primary Key
    :return: Dict, from cache, containing the progress key to track
    """
    _log.debug('In save_raw_data')

    prog_key = get_prog_key('save_raw_data', file_pk)
    initializing_key = {
        'status': 'not-started',
        'progress': 0,
        'progress_key': prog_key
    }
    set_cache(prog_key, initializing_key['status'], initializing_key)
    _save_raw_data.delay(file_pk)
    _log.debug('Returning from save_raw_data')
    result = get_cache(prog_key)
    return result


@shared_task
@lock_and_track
def match_buildings(file_pk):
    """
    kicks off system matching, returns progress key within the JSON response

    :param file_pk: ImportFile Primary Key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)
    prog_key = get_prog_key('match_buildings', file_pk)
    delete_cache(prog_key)
    if import_file.matching_done:
        return {
            'status': 'warning',
            'message': 'matching already complete',
            'progress_key': prog_key
        }

    if not import_file.mapping_done:
        # Re-add to the queue, hopefully our mapping will be done by then.
        match_buildings.apply_async(args=[file_pk], countdown=10, expires=20)
        return {
            'status': 'error',
            'message': 'waiting for mapping to complete',
            'progress_key': prog_key
        }

    if import_file.cycle is None:
        _log.warn("This should never happen in production")

    _match_properties_and_taxlots.delay(file_pk)

    return {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }


def _finish_matching(import_file, progress_key, data):
    import_file.matching_done = True
    import_file.mapping_completion = 100
    import_file.save()

    data['import_file_records'] = import_file.num_rows

    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': progress_key,
        'data': data
    }
    property_state_ids = list(PropertyState.objects.filter(import_file=import_file)
                              .exclude(data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT, DATA_STATE_DELETE])
                              .only('id').values_list('id', flat=True))
    taxlot_state_ids = list(TaxLotState.objects.filter(import_file=import_file)
                            .exclude(data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT, DATA_STATE_DELETE])
                            .only('id').values_list('id', flat=True))
    _data_quality_check(property_state_ids, taxlot_state_ids, import_file.id)
    set_cache(progress_key, result['status'], result)
    return result


def _find_matches(un_m_address, canonical_buildings_addresses):
    match_list = []
    if not un_m_address:
        return match_list
    for cb in canonical_buildings_addresses:
        if cb is None:
            continue
        if un_m_address.lower() == cb.lower():  # this second lower may be obsolete now
            match_list.append((un_m_address, 1))
    return match_list


# TODO: CLEANUP - What are we doing here?
md = MappingData()
ALL_COMPARISON_FIELDS = sorted(list(set([field['name'] for field in md.data])))
# Make sure that the import_file isn't part of the hash, as the import_file filename always has random characters
# appended to it in the uploads directory
try:
    ALL_COMPARISON_FIELDS.remove('import_file')
except ValueError:
    pass


def hash_state_object(obj, include_extra_data=True):
    def _get_field_from_obj(field_obj, field):
        if not hasattr(field_obj, field):
            return "FOO"  # Return a random value so we can distinguish between this and None.
        else:
            return getattr(field_obj, field)

    m = hashlib.md5()

    for f in ALL_COMPARISON_FIELDS:
        obj_val = _get_field_from_obj(obj, f)
        m.update(str(f))
        m.update(str(obj_val))
        # print "{}: {} -> {}".format(field, obj_val, m.hexdigest())

    if include_extra_data:
        add_dictionary_repr_to_hash(m, obj.extra_data)

    return m.hexdigest()


def add_dictionary_repr_to_hash(hash_obj, dict_obj):
    assert isinstance(dict_obj, dict)

    for (key, value) in sorted(dict_obj.items(), key=lambda x_y: x_y[0]):
        if isinstance(value, dict):
            add_dictionary_repr_to_hash(hash_obj, value)
        else:
            hash_obj.update(str(key))
            hash_obj.update(str(value))
    return hash_obj


def filter_duplicated_states(unmatched_states):
    """
    Takes a list of states, where some values may contain the same data
    as others, and returns two lists.  The first list consists of a
    single state for each equivalent set of states in
    unmatched_states.  The second list consists of all the
    non-representative states which (for example) could be deleted.

    :param unmatched_states: List, unmatched states
    :return:
    """

    hash_values = map(hash_state_object, unmatched_states)
    equality_classes = collections.defaultdict(list)

    for (ndx, hashval) in enumerate(hash_values):
        equality_classes[hashval].append(ndx)

    canonical_states = [unmatched_states[equality_list[0]] for equality_list in
                        equality_classes.values()]
    canonical_state_ids = set([s.pk for s in canonical_states])
    noncanonical_states = [u for u in unmatched_states if u.pk not in canonical_state_ids]

    return canonical_states, noncanonical_states


class EquivalencePartitioner(object):
    """Class for calculating equivalence classes on model States

    The EquivalencePartitioner is configured with a list of rules
    saying "two objects are equivalent if these two pieces of data are
    identical" or "two objects are not equivalent if these two pieces
    of data are different."  The partitioner then takes a group of
    objects (typically PropertyState and TaxLotState objects) and
    returns a partition of the objects (a collection of lists, where
    each object is a member of exactly one of the lists), where each
    list represents a "definitely distinct" element (i.e. two
    PropertyState objects with no values for pm_property_id,
    custom_id, etc may very well represent the same building, but we
    can't say that for certain).

    Some special cases that it handles based on SEED needs:

    - special treatment for matching based on multiple fields

    - Allowing one Field to hold "canonical" information (e.g. a
      building_id) and others (e.g. a custom_id) to hold potential
      information: when an alternate field (e.g. custom_id_1) is used,
      the logic does not necessarily assume the custom_id_1 means the
      portfolio manager id, unless p1.pm_property_id==p2.custom_id_1,
      etc.

    - equivalence/non-equivalence in both directions.  E.g. if
      ps1.pm_property_id == ps2.pm_property_id then ps1 represents the
      same object as ps2.  But if ps1.address_line_1 ==
      ps2.address_line_1, then ps1 is related to ps2, unless
      ps1.pm_property_id != ps2.pm_property_id, in which case ps1
      definitely is not the same as ps2.

    """

    def __init__(self, equivalence_class_description, identity_fields):
        """Constructor for class.

        Takes a list of mappings/conditions for object equivalence, as
        well as a list of identity fields (if these are not identical,
        the two objects are definitely different object)
        """

        self.equiv_comparison_key_func = self.make_resolved_key_calculation_function(
            equivalence_class_description)

        self.equiv_canonical_key_func = self.make_canonical_key_calculation_function(
            equivalence_class_description)

        self.identity_key_func = self.make_canonical_key_calculation_function(
            [(x,) for x in identity_fields])

        return

    @classmethod
    def make_default_state_equivalence(kls, equivalence_type):
        """
        Class for dynamically constructing an EquivalencePartitioner
        depending on the type of its parameter.
        """
        if equivalence_type == PropertyState:
            return kls.make_propertystate_equivalence()
        elif equivalence_type == TaxLotState:
            return kls.make_taxlotstate_equivalence()
        else:
            err_msg = ("Type '{}' does not have a default "
                       "EquivalencePartitioner set.".format(equivalence_type.__class__.__name__))
            raise ValueError(err_msg)

    @classmethod
    def make_propertystate_equivalence(kls):
        property_equivalence_fields = [
            ("pm_property_id", "custom_id_1"),
            ("custom_id_1",),
            ("normalized_address",)
        ]
        property_noequivalence_fields = ["pm_property_id"]

        return kls(property_equivalence_fields, property_noequivalence_fields)

    @classmethod
    def make_taxlotstate_equivalence(kls):
        """Return default EquivalencePartitioner for TaxLotStates

        Two tax lot states are identical if:

        - Their jurisdiction_tax_lot_ids are the same, which can be
          found in jurisdiction_tax_lot_ids or custom_id_1
        - Their custom_id_1 fields match
        - Their normalized addresses match

        They definitely do not match if :

        - Their jurisdiction_tax_lot_ids do not match.
        """
        tax_lot_equivalence_fields = [
            ("jurisdiction_tax_lot_id", "custom_id_1"),
            ("custom_id_1",),
            ("normalized_address",)
        ]
        tax_lot_noequivalence_fields = ["jurisdiction_tax_lot_id"]
        return kls(tax_lot_equivalence_fields, tax_lot_noequivalence_fields)

    @staticmethod
    def make_canonical_key_calculation_function(list_of_fieldlists):
        """Create a function that returns the "canonical" key for the object -
        where the official value for any position in the tuple can
        only come from the first object.
        """
        # The official key can only come from the first field in the
        # list.
        canonical_fields = [fieldlist[0] for fieldlist in list_of_fieldlists]
        return lambda obj: tuple([getattr(obj, field) for field in canonical_fields])

    @classmethod
    def make_resolved_key_calculation_function(kls, list_of_fieldlists):
        # This "resolves" the object to the best potential value in
        # each field.
        return (lambda obj: tuple(
            [kls._get_resolved_value_from_object(obj, list_of_fields) for list_of_fields in
             list_of_fieldlists]))

    @staticmethod
    def _get_resolved_value_from_object(obj, list_of_fields):
        for f in list_of_fields:
            val = getattr(obj, f)
            if val:
                return val
        else:
            return None

    @staticmethod
    def calculate_key_equivalence(key1, key2):
        for key1_value, key2_value in zip(key1, key2):
            if key1_value == key2_value and key1_value is not None:
                return True
        else:
            return False

    def calculate_comparison_key(self, obj):
        return self.equiv_comparison_key_func(obj)

    def calculate_canonical_key(self, obj):
        return self.equiv_canonical_key_func(obj)

    def calculate_identity_key(self, obj):
        return self.identity_key_func(obj)

    @staticmethod
    def key_needs_merging(original_key, new_key):
        return True in [not a and b for (a, b) in zip(original_key, new_key)]

    @staticmethod
    def merge_keys(key1, key2):
        return [a if a else b for (a, b) in zip(key1, key2)]

    @staticmethod
    def identities_are_different(key1, key2):
        for (x, y) in zip(key1, key2):
            if x is None or y is None:
                continue
            if x != y:
                return True
        else:
            return False

    def calculate_equivalence_classes(self, list_of_obj):
        """
        There is some subtlety with whether we use "comparison" keys
        or "canonical" keys.  This reflects the difference between
        searching vs. deciding information is official.

        For example, if we are trying to match on pm_property_id is,
        we may look in either pm_property_id or custom_id_1.  But if
        we are trying to ask what the pm_property_id of a State is
        that has a blank pm_property, we would not want to say the
        value in the custom_id must be the pm_property_id.

        :param list_of_obj:
        :return:
        """
        equivalence_classes = collections.defaultdict(list)
        identities_for_equivalence = {}

        for (ndx, obj) in enumerate(list_of_obj):
            cmp_key = self.calculate_comparison_key(obj)
            identity_key = self.calculate_identity_key(obj)

            for class_key in equivalence_classes:
                if self.calculate_key_equivalence(class_key,
                                                  cmp_key) and not self.identities_are_different(
                        identities_for_equivalence[class_key], identity_key):

                    equivalence_classes[class_key].append(ndx)

                    if self.key_needs_merging(class_key, cmp_key):
                        merged_key = self.merge_keys(class_key, cmp_key)
                        equivalence_classes[merged_key] = equivalence_classes.pop(class_key)
                        identities_for_equivalence[merged_key] = identity_key
                    break
            else:
                can_key = self.calculate_canonical_key(obj)
                equivalence_classes[can_key].append(ndx)
                identities_for_equivalence[can_key] = identity_key
        return equivalence_classes


def match_and_merge_unmatched_objects(unmatched_states, partitioner):
    """
    Take a list of unmatched_property_states or unmatched_tax_lot_states and returns a set of
    states that correspond to unmatched states.

    :param unmatched_states: list, PropertyStates or TaxLotStates
    :param partitioner: instance of EquivalencePartitioner
    :return: [list, list], merged_objects, equivalence_classes keys
    """
    _log.debug("Starting to map_and_merge_unmatched_objects")

    # Sort unmatched states/This should not be happening!
    unmatched_states.sort(key=lambda state: state.pk)

    def getattrdef(obj, attr, default):
        if hasattr(obj, attr):
            return getattr(obj, attr)
        else:
            return default

    keyfunction = lambda ndx: (getattrdef(unmatched_states[ndx], "release_date", None),
                               getattrdef(unmatched_states[ndx], "generation_date", None),
                               getattrdef(unmatched_states[ndx], "pk", None))

    # This removes any states that are duplicates,
    equivalence_classes = partitioner.calculate_equivalence_classes(unmatched_states)

    # For each of the equivalence classes, merge them down to a single
    # object of that type.
    merged_objects = []

    for (class_key, class_ndxs) in equivalence_classes.items():
        class_ndxs.sort(key=keyfunction)

        if len(class_ndxs) == 1:
            merged_objects.append(unmatched_states[class_ndxs[0]])
            continue

        unmatched_state_class = [unmatched_states[ndx] for ndx in class_ndxs]
        merged_result = unmatched_state_class[0]
        for unmatched in unmatched_state_class[1:]:
            merged_result, changes = save_state_match(merged_result, unmatched)

        else:
            merged_objects.append(merged_result)

    _log.debug("DONE with map_and_merge_unmatched_objects")
    return merged_objects, equivalence_classes.keys()


def merge_unmatched_into_views(unmatched_states, partitioner, org, import_file):
    """
    This is fairly inefficient, because we grab all the
    organization's entire PropertyViews at once.  Surely this can be
    improved, but the logic is unusual/particularly dynamic here, so
    hopefully this can be refactored into a better, purely database
    approach... Perhaps existing_view_states can wrap database
    calls. Still the abstractions are subtly different (can I
    refactor the partitioner to use Query objects); it may require a
    bit of thinking.

    :param unmatched_states:
    :param partitioner:
    :param org:
    :param import_file:
    :return:
    """

    current_match_cycle = import_file.cycle

    if isinstance(unmatched_states[0], PropertyState):
        ObjectViewClass = PropertyView
        ParentAttrName = "property"
    elif isinstance(unmatched_states[0], TaxLotState):
        ObjectViewClass = TaxLotView
        ParentAttrName = "taxlot"
    else:
        raise ValueError("Unknown class '{}' passed to merge_unmatched_into_views".format(
            type(unmatched_states[0])))

    class_views = ObjectViewClass.objects.filter(
        state__organization=org,
        cycle_id=current_match_cycle).select_related('state')
    existing_view_states = collections.defaultdict(dict)
    existing_view_state_hashes = set()
    for view in class_views:
        equivalence_can_key = partitioner.calculate_canonical_key(view.state)
        existing_view_states[equivalence_can_key][view.cycle] = view
        existing_view_state_hashes.add(hash_state_object(view.state))

    matched_views = []

    for unmatched in unmatched_states:

        unmatched_state_hash = hash_state_object(unmatched)
        if unmatched_state_hash in existing_view_state_hashes:
            # If an exact duplicate exists, delete the unmatched state
            unmatched.data_state = DATA_STATE_DELETE
            unmatched.save()

        else:
            # Look to see if there is a match among the property states of the object.

            # equiv_key = False
            # equiv_can_key = partitioner.calculate_canonical_key(unmatched)
            equiv_cmp_key = partitioner.calculate_comparison_key(unmatched)

            for key in existing_view_states:
                if partitioner.calculate_key_equivalence(key, equiv_cmp_key):
                    if current_match_cycle in existing_view_states[key]:
                        # There is an existing View for the current cycle that matches us.
                        # Merge the new state in with the existing one and update the view, audit log.
                        current_view = existing_view_states[key][current_match_cycle]
                        current_state = current_view.state

                        merged_state, change_ = save_state_match(current_state, unmatched)

                        current_view.state = merged_state
                        current_view.save()
                        matched_views.append(current_view)
                    else:
                        # Grab another view that has the same parent as
                        # the one we belong to.
                        cousin_view = existing_view_states[key].values()[0]
                        view_parent = getattr(cousin_view, ParentAttrName)
                        new_view = type(cousin_view)()
                        setattr(new_view, ParentAttrName, view_parent)
                        new_view.cycle = current_match_cycle
                        new_view.state = unmatched
                        try:
                            new_view.save()
                            matched_views.append(new_view)
                        except IntegrityError:
                            _log.warn("Unable to save the new view as it already exists in the db")

                    break
            else:
                # Create a new object/view for the current object.
                created_view = unmatched.promote(current_match_cycle)
                matched_views.append(created_view)

    return list(set(matched_views))


@shared_task
@lock_and_track
def _match_properties_and_taxlots(file_pk):
    """
    Match the properties and taxlots

    :param file_pk: ImportFile Primary Key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)
    prog_key = get_prog_key('match_buildings', file_pk)

    # Don't query the org table here, just get the organization from the import_record
    org = import_file.import_record.super_organization

    # Return a list of all the properties/tax lots based on the import file.
    all_unmatched_properties = import_file.find_unmatched_property_states()
    unmatched_properties = []
    unmatched_tax_lots = []
    duplicates_of_existing_property_states = []
    duplicates_of_existing_taxlot_states = []
    if all_unmatched_properties:
        # Filter out the duplicates within the import file.
        unmatched_properties, duplicate_property_states = filter_duplicated_states(
            all_unmatched_properties)

        property_partitioner = EquivalencePartitioner.make_default_state_equivalence(PropertyState)

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner, while ignoring duplicates.
        unmatched_properties, property_equivalence_keys = match_and_merge_unmatched_objects(
            unmatched_properties,
            property_partitioner)

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        merged_property_views = merge_unmatched_into_views(
            unmatched_properties,
            property_partitioner,
            org,
            import_file)

        # Filter out the exact duplicates found in the previous step
        duplicates_of_existing_property_states = [state for state in unmatched_properties
                                                  if state.data_state == DATA_STATE_DELETE]
        unmatched_properties = [state for state in unmatched_properties
                                if state not in duplicates_of_existing_property_states]
    else:
        duplicate_property_states = []
        merged_property_views = []

    # Do the same process with the TaxLots.
    all_unmatched_tax_lots = import_file.find_unmatched_tax_lot_states()

    if all_unmatched_tax_lots:
        # Filter out the duplicates.  Do we actually want to delete them
        # here?  Mark their abandonment in the Audit Logs?
        unmatched_tax_lots, duplicate_tax_lot_states = filter_duplicated_states(
            all_unmatched_tax_lots)

        taxlot_partitioner = EquivalencePartitioner.make_default_state_equivalence(TaxLotState)

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner.
        unmatched_tax_lots, taxlot_equivalence_keys = match_and_merge_unmatched_objects(
            unmatched_tax_lots,
            taxlot_partitioner)

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        merged_taxlot_views = merge_unmatched_into_views(
            unmatched_tax_lots,
            taxlot_partitioner,
            org,
            import_file)

        # Filter out the exact duplicates found in the previous step
        duplicates_of_existing_taxlot_states = [state for state in unmatched_tax_lots
                                                if state.data_state == DATA_STATE_DELETE]
        unmatched_tax_lots = [state for state in unmatched_tax_lots
                              if state not in duplicates_of_existing_taxlot_states]
    else:
        duplicate_tax_lot_states = []
        merged_taxlot_views = []

    pair_new_states(merged_property_views, merged_taxlot_views)

    # Mark all the unmatched objects as done with matching and mapping
    # There should be some kind of bulk-update/save thing we can do to
    # improve upon this.
    for state in chain(unmatched_properties, unmatched_tax_lots):
        state.data_state = DATA_STATE_MATCHING
        state.save()

    for state in map(lambda x: x.state, chain(merged_property_views, merged_taxlot_views)):
        state.data_state = DATA_STATE_MATCHING
        # The merge state seems backwards, but it isn't for some reason, if they are not marked as
        # MERGE_STATE_MERGED when called in the merge_unmatched_into_views, then they are new.
        if state.merge_state != MERGE_STATE_MERGED:
            state.merge_state = MERGE_STATE_NEW
        state.save()

    for state in chain(duplicate_property_states, duplicate_tax_lot_states):
        state.data_state = DATA_STATE_DELETE
        # state.merge_state = MERGE_STATE_DUPLICATE
        state.save()

    data = {
        'all_unmatched_properties': len(all_unmatched_properties),
        'all_unmatched_tax_lots': len(all_unmatched_tax_lots),
        'unmatched_properties': len(unmatched_properties),
        'unmatched_tax_lots': len(unmatched_tax_lots),
        'duplicate_property_states': len(duplicate_property_states),
        'duplicate_tax_lot_states': len(duplicate_tax_lot_states),
        'duplicates_of_existing_property_states': len(duplicates_of_existing_property_states),
        'duplicates_of_existing_taxlot_states': len(duplicates_of_existing_taxlot_states)
    }

    return _finish_matching(import_file, prog_key, data)


def list_canonical_property_states(org_id):
    """
    Return a QuerySet of the property states that are part of the inventory

    Args:
        org_id: Organization ID

    Returns:
        QuerySet

    """
    pvs = PropertyView.objects.filter(
        state__organization=org_id,
        state__data_state__in=[DATA_STATE_MATCHING]
    ).select_related('state')

    ids = [p.state.id for p in pvs]
    return PropertyState.objects.filter(pk__in=ids)


def query_property_matches(properties, pm_id, custom_id):
    """
    Returns query set of PropertyStates that match at least one of the specified ids

    :param properties: QuerySet, PropertyStates
    :param pm_id: string, PM Property ID
    :param custom_id: String, Custom ID
    :return: QuerySet of objects that meet criteria.
    """

    """"""
    params = []
    # Not sure what the point of this logic is here. If we are passing in a custom_id then
    # why would we want to check pm_property_id against the custom_id, what if we pass both in?
    # Seems like this favors pm_id
    if pm_id:
        params.append(Q(pm_property_id=pm_id))
        params.append(Q(custom_id_1=pm_id))
    if custom_id:
        params.append(Q(pm_property_id=custom_id))
        params.append(Q(custom_id_1=custom_id))

    if not params:
        # Return an empty QuerySet if we don't have any params.
        return properties.none()

    return properties.filter(reduce(operator.or_, params))


# TODO: Move this should be on the PropertyState (or property) class
def is_same_snapshot(s1, s2):
    fields_to_ignore = ["id",
                        "created",
                        "modified",
                        "match_type",
                        "confidence",
                        "source_type",
                        "canonical_building_id",
                        "import_file_id",
                        "_state",
                        "_import_file_cache",
                        "import_record"]

    for k, v in s1.__dict__.items():
        # ignore anything that starts with an underscore
        if k[0] == "_":
            continue
        # also need to ignore any field with "_source" in it
        # TODO: Remove _source as this is no longer in the database
        if "_source" in k:
            continue
        if k in fields_to_ignore:
            continue
        if k not in s2.__dict__ or s2.__dict__[k] != v:
            return False

    return True


def save_state_match(state1, state2):
    merged_state = type(state1).objects.create(organization=state1.organization)

    merged_state, changes = merging.merge_state(merged_state,
                                                state1, state2,
                                                merging.get_state_attrs([state1, state2]),
                                                default=state2)

    AuditLogClass = PropertyAuditLog if isinstance(merged_state, PropertyState) else TaxLotAuditLog

    assert AuditLogClass.objects.filter(state=state1).count() >= 1
    assert AuditLogClass.objects.filter(state=state2).count() >= 1

    # NJACHECK - is this logic correct?
    state_1_audit_log = AuditLogClass.objects.filter(state=state1).first()
    state_2_audit_log = AuditLogClass.objects.filter(state=state2).first()

    AuditLogClass.objects.create(organization=state1.organization,
                                 parent1=state_1_audit_log,
                                 parent2=state_2_audit_log,
                                 parent_state1=state1,
                                 parent_state2=state2,
                                 state=merged_state,
                                 name='System Match',
                                 description='Automatic Merge',
                                 import_filename=None,
                                 record_type=AUDIT_IMPORT)

    # print "merging two properties {}/{}".format(ps1_pk, ps2_pk)
    # pp(ps1)
    # pp(ps2)
    # pp(merged_property_state)

    # Set the merged_state to merged
    merged_state.merge_state = MERGE_STATE_MERGED
    merged_state.save()

    return merged_state, False


def pair_new_states(merged_property_views, merged_taxlot_views):
    """
    Pair new states from lists of property views and tax lot views

    :param merged_property_views: list, merged property views
    :param merged_taxlot_views: list, merged tax lot views
    :return: None
    """
    if not merged_property_views and not merged_taxlot_views:
        return

    # Not sure what the below cycle code does.
    cycle = chain(merged_property_views, merged_taxlot_views).next().cycle

    tax_cmp_fmt = [('jurisdiction_tax_lot_id', 'custom_id_1'),
                   ('custom_id_1',),
                   ('normalized_address',),
                   ('custom_id_1',),
                   ('custom_id_1',)]

    prop_cmp_fmt = [('lot_number', 'custom_id_1'),
                    ('custom_id_1',),
                    ('normalized_address',),
                    ('pm_property_id',),
                    ('jurisdiction_property_id',)]

    tax_comparison_fields = sorted(list(set(chain.from_iterable(tax_cmp_fmt))))
    prop_comparison_fields = sorted(list(set(chain.from_iterable(prop_cmp_fmt))))

    tax_comparison_field_names = map(lambda s: "state__{}".format(s), tax_comparison_fields)
    prop_comparison_field_names = map(lambda s: "state__{}".format(s), prop_comparison_fields)

    # This is a not so nice hack. but it's the only special case/field
    # that isn't on the join to the State.
    tax_comparison_fields.insert(0, 'pk')
    prop_comparison_fields.insert(0, 'pk')
    tax_comparison_field_names.insert(0, 'pk')
    prop_comparison_field_names.insert(0, 'pk')

    view = chain(merged_property_views, merged_taxlot_views).next()
    cycle = view.cycle
    org = view.state.organization

    global taxlot_m2m_keygen
    global property_m2m_keygen

    taxlot_m2m_keygen = EquivalencePartitioner(tax_cmp_fmt, ["jurisdiction_tax_lot_id"])
    property_m2m_keygen = EquivalencePartitioner(prop_cmp_fmt,
                                                 ["pm_property_id", "jurisdiction_property_id"])

    property_views = PropertyView.objects.filter(state__organization=org, cycle=cycle).values_list(
        *prop_comparison_field_names)
    taxlot_views = TaxLotView.objects.filter(state__organization=org, cycle=cycle).values_list(
        *tax_comparison_field_names)

    # For each of the view objects, make an
    prop_type = namedtuple("Prop", prop_comparison_fields)
    taxlot_type = namedtuple("TL", tax_comparison_fields)

    # Makes object with field_name->val attributes on them.
    property_objects = [prop_type(*attr) for attr in property_views]
    taxlot_objects = [taxlot_type(*attr) for attr in taxlot_views]

    # NA: I believe this is incorrect, but doing this for simplicity
    # now. The logic that is being missed is a pretty extreme corner
    # case.

    # NA: I should generate one key for each property for each thing in it's lot number state.

    # property_keys = {property_m2m_keygen.calculate_comparison_key(p): p.pk for p in property_objects}
    # taxlot_keys = [taxlot_m2m_keygen.calculate_comparison_key(tl): tl.pk for tl in taxlot_objects}

    # Calculate a key for each of the split fields.
    property_keys_orig = dict(
        [(property_m2m_keygen.calculate_comparison_key(p), p.pk) for p in property_objects])

    # property_keys = copy.deepcopy(property_keys_orig)

    # Do this inelegant step to make sure we are correctly splitting.
    property_keys = collections.defaultdict(list)
    for k in property_keys_orig:
        if k[0] and ";" in k[0]:
            for lotnum in map(lambda x: x.strip(), k[0].split(";")):
                k_copy = list(copy.deepcopy(k))
                k_copy[0] = lotnum
                property_keys[tuple(k_copy)] = property_keys_orig[k]
        else:
            property_keys[k] = property_keys_orig[k]

    taxlot_keys = dict(
        [(taxlot_m2m_keygen.calculate_comparison_key(p), p.pk) for p in taxlot_objects])

    # property_comparison_keys = {property_m2m_keygen.calculate_comparison_key_key(p): p.pk for p in property_objects}
    # property_canonical_keys = {property_m2m_keygen.calculate_canonical_key(p): p.pk for p in property_objects}

    possible_merges = []  # List of prop.id, tl.id merges.

    for pv in merged_property_views:
        # if pv.state.lot_number and ";" in pv.state.lot_number:
        #     pdb.set_trace()

        pv_key = property_m2m_keygen.calculate_comparison_key(pv.state)
        # TODO: Refactor pronto.  Iterating over the tax lot is bad implementation.
        for tlk in taxlot_keys:
            if pv_key[0] and ";" in pv_key[0]:
                for lotnum in map(lambda x: x.strip(), pv_key[0].split(";")):
                    pv_key_copy = list(copy.deepcopy(pv_key))
                    pv_key_copy[0] = lotnum
                    pv_key_copy = tuple(pv_key_copy)
                    if property_m2m_keygen.calculate_key_equivalence(pv_key_copy, tlk):
                        possible_merges.append((property_keys[pv_key_copy], taxlot_keys[tlk]))
            else:
                if property_m2m_keygen.calculate_key_equivalence(pv_key, tlk):
                    possible_merges.append((property_keys[pv_key], taxlot_keys[tlk]))

    for tlv in merged_taxlot_views:
        tlv_key = taxlot_m2m_keygen.calculate_comparison_key(tlv.state)
        for pv_key in property_keys:
            if property_m2m_keygen.calculate_key_equivalence(tlv_key, pv_key):
                possible_merges.append((property_keys[pv_key], taxlot_keys[tlv_key]))

    for m2m in set(possible_merges):
        pv_pk, tlv_pk = m2m

        # PropertyView.objects.get(pk=pv_pk)
        # TaxLotView.objects.get(pk=tlv_pk)

        connection = TaxLotProperty.objects.filter(
            property_view_id=pv_pk,
            taxlot_view_id=tlv_pk
        ).count()

        if connection:
            continue

        is_primary = TaxLotProperty.objects.filter(property_view_id=pv_pk).count() == 0
        m2m_join = TaxLotProperty(
            property_view_id=pv_pk,
            taxlot_view_id=tlv_pk,
            cycle=cycle,
            primary=is_primary
        )
        m2m_join.save()

    return
