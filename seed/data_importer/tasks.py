# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import

import collections
import copy
import datetime
import hashlib
import operator
import re
import string
import time
import traceback
from _csv import Error
from collections import namedtuple
from functools import reduce
from itertools import chain

from celery import chord
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.models import Q
from unidecode import unidecode

from seed.cleansing.models import Cleansing
from seed.cleansing.tasks import (
    finish_cleansing,
    cleanse_data_chunk,
)
from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
    STATUS_READY_TO_MERGE,
    # DuplicateDataError,
)
from seed.decorators import get_prog_key
from seed.decorators import lock_and_track
from seed.green_button import xml_importer
from seed.lib.mappings.mapping_data import MappingData
from seed.lib.mcm import cleaners, mapper, reader
from seed.lib.mcm.data.ESPM import espm as espm_schema
from seed.lib.mcm.data.SEED import seed as seed_schema
from seed.lib.mcm.mapper import expand_rows
from seed.lib.mcm.utils import batch
from seed.lib.superperms.orgs.models import Organization
from seed.models import (
    ASSESSED_BS,
    ASSESSED_RAW,
    # BS_VALUES_LIST,
    GREEN_BUTTON_BS,
    GREEN_BUTTON_RAW,
    PORTFOLIO_BS,
    PORTFOLIO_RAW,
    SYSTEM_MATCH,
    Column,
    ColumnMapping,
    # find_canonical_building_values,
    # initialize_canonical_building,
    # save_snapshot_match,
    # BuildingSnapshot,
    PropertyState,
    PropertyView,
    TaxLotView,
    TaxLotState,
    DATA_STATE_IMPORT,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    DATA_STATE_DELETE,
)
from seed.models import PropertyAuditLog
from seed.models import TaxLotAuditLog
from seed.models import TaxLotProperty
from seed.models.auditlog import AUDIT_IMPORT
from seed.utils.buildings import get_source_type
from seed.utils.cache import set_cache, increment_cache, get_cache

_log = get_task_logger(__name__)

# Maximum number of possible matches under which we'll allow a system match.
MAX_SEARCH = 5
# Minimum confidence of two buildings being related.
MIN_CONF = .80  # TODO: not used anymore?
# Knows how to clean floats for ESPM data.
ASSESSED_CLEANER = cleaners.Cleaner(seed_schema.schema)
PORTFOLIO_CLEANER = cleaners.Cleaner(espm_schema.schema)
PUNCT_REGEX = re.compile('[{0}]'.format(
    re.escape(string.punctuation)
))

STR_TO_CLASS = {"TaxLotState": TaxLotState, "PropertyState": PropertyState}


def get_cache_increment_value(chunk):
    denom = len(chunk) or 1
    return 1.0 / denom * 100


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

    import_record.finish_time = datetime.datetime.utcnow()
    import_record.status = STATUS_READY_TO_MERGE
    import_record.save()


@shared_task
def finish_mapping(file_pk):
    import_file = ImportFile.objects.get(pk=file_pk)
    import_file.mapping_done = True
    import_file.save()
    finish_import_record(import_file.import_record.pk)
    prog_key = get_prog_key('map_data', file_pk)
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)

    # now call cleansing
    _cleanse_data(file_pk)


def _translate_unit_to_type(unit):
    if unit is None or unit == 'String':
        return 'str'

    return unit.lower()


def _build_cleaner(org):
    """Return a cleaner instance that knows about a mapping's unit types.

    Basically, this just tells us how to try and cast types during cleaning
    based on the Column definition in the database.

    :param org: superperms.orgs.Organization instance.
    :returns: dict of dicts. {'types': {'col_name': 'type'},}
    """
    units = {'types': {}}
    for column in Column.objects.filter(
            mapped_mappings__super_organization=org
    ).select_related('unit'):
        column_type = 'str'
        if column.unit:
            column_type = _translate_unit_to_type(
                column.unit.get_unit_type_display()
            )
        units['types'][column.column_name] = column_type

    # TODO(gavin): make this completely data-driven. # NL !!!
    # Update with our predefined types for our BuildingSnapshot column types.
    units['types'].update(seed_schema.schema['types'])

    return cleaners.Cleaner(units)


@shared_task
def map_row_chunk(ids, file_pk, source_type, prog_key, increment, *args, **kwargs):
    """Does the work of matching a mapping to a source type and saving

    :param ids: list of PropertyState IDs to map.
    :param file_pk: int, the PK for an ImportFile obj.
    :param source_type: int, represented by either ASSESSED_RAW or PORTFOLIO_RAW.
    :param prog_key: string, key of the progress key
    :param increment: double, value by which to increment progress key
    :param cleaner: (optional), the cleaner class you want to send to mapper.map_row.
                    (e.g. turn numbers into floats.).
    :param raw_ids: (optional kwarg), the list of ids in chunk order.

    """

    _log.debug("Mapping row chunks")
    import_file = ImportFile.objects.get(pk=file_pk)
    save_type = PORTFOLIO_BS
    if source_type == ASSESSED_RAW:
        save_type = ASSESSED_BS

    org = Organization.objects.get(pk=import_file.import_record.super_organization.pk)

    table_mappings = ColumnMapping.get_column_mappings_by_table_name(org)

    # TODO: **TOTAL TERRIBLE HACK HERE**
    # For some reason the mappings that got created previously don't
    # always have the table class in them.  To get this working for
    # the demo this is an infix place, but is absolutely terrible and
    # should be removed ASAP!!!!!
    if 'PropertyState' not in table_mappings and 'TaxLotState' in table_mappings and '' in table_mappings:
        _log.error("this code should not be running here...")
        debug_inferred_prop_state_mapping = table_mappings['']
        table_mappings['PropertyState'] = debug_inferred_prop_state_mapping

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

    # Add custom mappings for cross-related data. Right now these are hard coded, but could
    # be a setting if so desired.
    if delimited_fields and delimited_fields[
            'jurisdiction_tax_lot_id'] and 'PropertyState' in table_mappings.keys():
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
            _log.debug("Expand row is set to {}".format(expand_row))

            delimited_field_list = []
            for _, v in delimited_fields.iteritems():
                delimited_field_list.append(v['from_field'])

            _log.debug("delimited_field_list is set to {}".format(delimited_field_list))

            # Weeee... the data are in the extra_data column.
            for row in expand_rows(original_row.extra_data, delimited_field_list, expand_row):
                # TODO: during the mapping the data are saved back in the database
                # If the user decided to not use the mapped data and go back and remap
                # then the data will forever be in the property state table for
                # no reason. FIX THIS!

                map_model_obj = mapper.map_row(
                    row,
                    mappings,
                    STR_TO_CLASS[table],
                    extra_data_fields,
                    cleaner=map_cleaner,
                    *args,
                    **kwargs
                )

                # save cross related data, that is data that needs to go into the other model's
                # collection as well.

                # Assign some other arguments here
                map_model_obj.import_file = import_file
                map_model_obj.source_type = save_type
                map_model_obj.organization = import_file.import_record.super_organization  # Not the best place..
                if hasattr(map_model_obj, 'data_state'):
                    map_model_obj.data_state = DATA_STATE_MAPPING
                if hasattr(map_model_obj, 'organization'):
                    map_model_obj.organization = import_file.import_record.super_organization
                if hasattr(map_model_obj, 'clean'):
                    map_model_obj.clean()

                # --- BEGIN TEMP HACK ----
                # TODO: fix these in the cleaner, but for now just get things to work, yuck.
                # It appears that the cleaner pulls from some schema somewhere that defines the
                # data types... stay tuned.
                if hasattr(map_model_obj,
                           'recent_sale_date') and map_model_obj.recent_sale_date == '':
                    _log.debug("recent_sale_date was an empty string, setting to None")
                    map_model_obj.recent_sale_date = None
                if hasattr(map_model_obj,
                           'generation_date') and map_model_obj.generation_date == '':
                    _log.debug("generation_date was an empty string, setting to None")
                    map_model_obj.generation_date = None
                if hasattr(map_model_obj, 'release_date') and map_model_obj.release_date == '':
                    _log.debug("release_date was an empty string, setting to None")
                    map_model_obj.release_date = None
                if hasattr(map_model_obj, 'year_ending') and map_model_obj.year_ending == '':
                    _log.debug("year_ending was an empty string, setting to None")
                    map_model_obj.year_ending = None

                # TODO: Second temporary hack.  This should not happen but somehow it does.
                # Removing hack... this should be handled on the front end.
                # if isinstance(map_model_obj, PropertyState):
                #     if map_model_obj.pm_property_id is None and map_model_obj.address_line_1 is None and map_model_obj.custom_id_1 is None:
                #         print "Skipping!"
                #         continue
                # --- END TEMP HACK ----

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

                    # Create an audit log record for the new
                    # map_model_obj that was created.

                    AuditLogClass = PropertyAuditLog if isinstance(map_model_obj,
                                                                   PropertyState) else TaxLotAuditLog
                    AuditLogClass.objects.create(organization=org,
                                                 state=map_model_obj,
                                                 name='Import Creation',
                                                 description='Creation from Import file.',
                                                 import_filename=import_file,
                                                 record_type=AUDIT_IMPORT)

                except:
                    # Could not save the record for some reason. Report out and keep moving
                    # TODO: Need to address this and report back to the user which records were not imported  #noqa
                    _log.error("ERROR: Could not save the model with row {}".format(row))

        # Make sure that we've saved all of the extra_data column names from the first item in list
        if map_model_obj:
            Column.save_column_names(map_model_obj)

    increment_cache(prog_key, increment)


@shared_task
@lock_and_track
def _map_data(file_pk, *args, **kwargs):
    """Get all of the raw data and process it using appropriate mapping.
    @lock_and_track returns a progress_key

    :param file_pk: int, the id of the import_file we're working with.

    """
    _log.debug("Starting to map the data")
    prog_key = get_prog_key('map_data', file_pk)
    import_file = ImportFile.objects.get(pk=file_pk)
    # Don't perform this task if it's already been completed.
    if import_file.mapping_done:
        _log.debug("_map_data mapping_done is true")
        result = {
            'status': 'warning',
            'progress': 100,
            'message': 'mapping already complete',
            'progress_key': prog_key
        }
        set_cache(prog_key, result['status'], result)
        return result

    # If we haven't finished saving, we shouldn't proceed with mapping
    # Re-queue this task.
    if not import_file.raw_save_done:
        _log.debug("_map_data raw_save_done is false, queueing the task until raw_save finishes")
        map_data.apply_async(args=[file_pk], countdown=60, expires=120)
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
    tasks = [map_row_chunk.s(ids, file_pk, source_type, prog_key, increment)
             for ids in id_chunks]

    if tasks:
        # specify the chord as an immutable with .si
        chord(tasks, interval=15)(finish_mapping.si(file_pk))
    else:
        _log.debug("Not creating finish_mapping chord, calling directly")
        finish_mapping.si(file_pk)


@shared_task
@lock_and_track
def _cleanse_data(file_pk, record_type='property'):
    """

    Get the mapped data and run the cleansing class against it in chunks. The
    mapped data are pulled from the PropertyState(or Taxlot) table.

    @lock_and_track returns a progress_key

    :param file_pk: int, the id of the import_file we're working with.
    :param report: string, 'property' or 'taxlot', defaults to property

    """
    # TODO Since this function was previously hardcoded to use PropertyState,
    # but the functions/methods it calls can now handle both, I converted
    # this function and had record_type to  default to PropertyState,
    # I did not change anything where it gets called.

    import_file = ImportFile.objects.get(pk=file_pk)

    source_type_dict = {
        'Portfolio Raw': PORTFOLIO_BS,
        'Assessed Raw': ASSESSED_BS,
        'Green Button Raw': GREEN_BUTTON_BS,
    }

    # This is non-ideal, but the source type of the input file is never
    # updated, but the data are stages as if it were.
    #
    # After the mapping stage occurs, the data end up in the PropertyState
    # table under the *_BS value.
    source_type = source_type_dict.get(import_file.source_type, ASSESSED_BS)

    model = {
        'property': PropertyState, 'taxlot': TaxLotState
    }.get(record_type)

    qs = model.objects.filter(
        import_file=import_file,
        source_type=source_type,
    ).only('id').iterator()

    # initialize the cache for the cleansing results using the cleansing static method
    Cleansing.initialize_cache(file_pk)

    prog_key = get_prog_key('cleanse_data', file_pk)

    id_chunks = [[obj.id for obj in chunk] for chunk in batch(qs, 100)]
    increment = get_cache_increment_value(id_chunks)
    tasks = [
        cleanse_data_chunk.s(record_type, ids, file_pk, increment)
        for ids in id_chunks
    ]

    if tasks:
        # specify the chord as an immutable with .si
        chord(tasks, interval=15)(finish_cleansing.si(file_pk))
    else:
        finish_cleansing.s(file_pk)

    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    return result


@shared_task
def map_data(file_pk, *args, **kwargs):
    """Small wrapper to ensure we isolate our mapping process from requests."""
    _map_data.delay(file_pk)
    prog_key = get_prog_key('map_data', file_pk)
    return {'status': 'started', 'progress_key': prog_key}


@shared_task
def _save_raw_data_chunk(chunk, file_pk, prog_key, increment, *args, **kwargs):
    """Save the raw data to the database."""
    import_file = ImportFile.objects.get(pk=file_pk)

    # Save our "column headers" and sample rows for F/E.
    source_type = get_source_type(import_file)
    for c in chunk:
        raw_property = PropertyState(organization=import_file.import_record.super_organization)
        raw_property.import_file = import_file  # not defined in new data model

        # sanitize c and remove any diacritics
        new_chunk = {}
        for k, v in c.iteritems():
            # remove extra spaces surrounding keys
            key = k.strip()
            if isinstance(v, unicode):
                new_chunk[key] = unidecode(v)
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

        # set_initial_sources(raw_property)
        raw_property.save()

    # Indicate progress
    increment_cache(prog_key, increment)
    _log.debug('Returning from _save_raw_data_chunk')

    return True


@shared_task
def finish_raw_save(file_pk):
    """
    Finish importing the raw file.

    :param results: results from the other tasks before the chord ran
    :param file_pk: ID of the file that was being imported
    :return: None
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
    first_row = parser.headers()
    first_five_rows = parser.first_five_rows

    _log.debug(first_five_rows)

    import_file.cached_second_to_fifth_row = "\n".join(first_five_rows)
    if first_row:
        first_row = reader.ROW_DELIMITER.join(first_row)
    import_file.cached_first_row = first_row or ''
    import_file.save()


@shared_task
@lock_and_track
def _save_raw_green_button_data(file_pk, *args, **kwargs):
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
            return _save_raw_green_button_data(file_pk, *args, **kwargs)

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
    _log.debug('In save_raw_data')

    prog_key = get_prog_key('save_raw_data', file_pk)
    initializing_key = {
        'status': 'not-started',
        'progress': 0,
        'progress_key': prog_key
    }
    set_cache(prog_key, initializing_key['status'], initializing_key)
    _save_raw_data.delay(file_pk, *args, **kwargs)
    _log.debug('Returning from save_raw_data')
    result = get_cache(prog_key)
    return result


# TODO: Not used -- remove
def _stringify(values):
    """Take iterable of str and NoneTypes and reduce to space sep. str."""
    return ' '.join(
        [PUNCT_REGEX.sub('', value.lower()) for value in values if value]
    )


# def handle_results(results, b_idx, can_rev_idx, unmatched_list, user_pk):
#     """Seek IDs and save our snapshot match.
#
#     :param results: list of tuples. [('match', 0.99999),...]
#     :param b_idx: int, the index of the current building in the unmatched_list.
#     :param can_rev_idx: dict, reverse index from match -> canonical PK.
#     :param user_pk: user ID, used for AuditLog logging
#     :unmatched_list: list of dicts, the result of a values_list query for
#         unmatched PropertyState.
#
#     """
#     match_string, confidence = results[0]  # We always care about closest match
#     match_type = SYSTEM_MATCH
#     # If we passed the minimum threshold, we're here, but we need to
#     # distinguish probable matches from good matches.
#     if confidence < getattr(settings, 'MATCH_MED_THRESHOLD', 0.7):
#         match_type = POSSIBLE_MATCH
#
#     can_snap_pk = can_rev_idx[match_string]
#     building_pk = unmatched_list[b_idx][0]  # First element is PK
#
#     bs, changes = save_snapshot_match(
#         can_snap_pk,
#         building_pk,
#         confidence=confidence,
#         match_type=match_type,
#         default_pk=building_pk,
#     )
#     canon = bs.canonical_building
#     action_note = 'System matched building.'
#     if changes:
#         action_note += "  Fields changed in cannonical building:\n"
#         for change in changes:
#             action_note += "\t{field}:\t".format(
#                 field=change["field"].replace("_", " ").replace("-",
#                                                                 "").capitalize(),
#             )
#             if "from" in change:
#                 action_note += "From:\t{prev}\tTo:\t".format(
#                     prev=change["from"])
#
#             action_note += "{value}\n".format(value=change["to"])
#         action_note = action_note[:-1]
#     AuditLog.objects.create(
#         user_id=user_pk,
#         content_object=canon,
#         action_note=action_note,
#         action='save_system_match',
#         organization=bs.super_organization,
#     )


@shared_task
@lock_and_track
def match_buildings(file_pk, user_pk):
    """
    kicks off system matching, returns progress key within the JSON response
    """
    import_file = ImportFile.objects.get(pk=file_pk)
    prog_key = get_prog_key('match_buildings', file_pk)
    if import_file.matching_done:
        return {
            'status': 'warning',
            'message': 'matching already complete',
            'progress_key': prog_key
        }

    if not import_file.mapping_done:
        # Re-add to the queue, hopefully our mapping will be done by then.
        match_buildings.apply_async(
            args=[file_pk, user_pk], countdown=10, expires=20
        )
        return {
            'status': 'error',
            'message': 'waiting for mapping to complete',
            'progress_key': prog_key
        }

    if import_file.cycle is None:
        print "DANGER"
    _match_properties_and_taxlots.delay(file_pk, user_pk)

    return {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }


# def handle_id_matches(unmatched_property_states, unmatched_property_state, import_file, user_pk):
#     """
#     Deals with exact matches in the IDs of buildings.

#     :param unmatched_property_states:
#     :param unmatched_property_state:
#     :param import_file:
#     :param user_pk:
#     :return:
#     """

#     # TODO: this only works for PropertyStates right now because the unmatched_property_states is a QuerySet
#     # of PropertyState of which have the .pm_property_id and .custom_id_1 fields.
#     id_matches = query_property_matches(
#         unmatched_property_states,
#         unmatched_property_state.pm_property_id,
#         unmatched_property_state.custom_id_1
#     )
#     if not id_matches.exists():
#         return

#     # Check to see if there are any duplicates here
#     # for match in id_matches:
#     #     if is_same_snapshot(unmatched_property_states, match):
#     #         raise DuplicateDataError(match.pk)

#     # Reading the code, this appears to be the intention of the code.

#     # Combinations returns every combination once without regard to
#     # order and does not include self-combinations.
#     # e.g combinations(ABC) = AB, AC, BC
#     for (m1, m2) in itertools.combinations(id_matches, 2):
#         if is_same_snapshot(m1, m2):
#             raise DuplicateDataError(match.pk)

#     # Merge Everything Together
#     merged_result = id_matches[0]
#     for match in id_matches:
#         merged_result, changes = save_state_match(merged_result,
#                                                   match,
#                                                   confidence=0.9,
#                                                   match_type=SYSTEM_MATCH,
#                                                   user=import_file.import_record.owner
#                                                   # What does this param do?
#                                                   # default_pk=unmatched_property_states.pk
#         )
#     else:
#         # TODO - coordinate with Nick on how to get the correct cycle,
#         # rather than the most recent one.

#         org = Organization.objects.filter(users=import_file.import_record.owner).first()
#         default_cycle = Cycle.objects.filter(organization = org).order_by('-start').first()
#         merged_result.promote(default_cycle) # Make sure this creates the View.

#         # AuditLog.objects.create(
#         #     user_id=user_pk,
#         #     content_object=canon,
#         #     action_note=action_note,
#         #     action='save_system_match',
#         #     organization=unmatched_property_states.super_organization,
#         # )

#     # Returns the most recent child of all merging.
#     return merged_result


# def merge_property_matches(match.

def _finish_matching(import_file, progress_key):
    import_file.matching_done = True
    import_file.mapping_completion = 100
    import_file.save()

    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': progress_key
    }
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


# TODO: These are bad bad fields!
#       Not quite sure what this means?
# NL: yeah what does this mean?!

md = MappingData()
ALL_COMPARISON_FIELDS = sorted(list(set([field['name'] for field in md.data])))


# all_comparison_fields = sorted(list(set(chain(tax_lot_comparison_fields, property_comparison_fields))))


def hash_state_object(obj, include_extra_data=True):
    def _getFieldFromObj(obj, field):
        if not hasattr(obj, field):
            return "FOO"  # Return a random value so we can distinguish between this and None.
        else:
            return getattr(obj, field)

    m = hashlib.md5()

    for field in ALL_COMPARISON_FIELDS:
        obj_val = _getFieldFromObj(obj, field)
        m.update(str(field))
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
    """Takes a list of states, where some values may contain the same data
    as others, and returns two lists.  The first list consists of a
    single state for each equivalent set of states in
    unmatched_states.  The second list consists of all the
    non-representative states which (for example) could be deleted.
    """

    hash_values = map(hash_state_object, unmatched_states)
    equality_classes = collections.defaultdict(list)

    for (ndx, hashval) in enumerate(hash_values):
        equality_classes[hashval].append(ndx)

    def union_lol(lol):
        """Union of list of lists"""
        return list(set(chain.from_iterable(lol)))

    canonical_states = [unmatched_states[equality_list[0]] for equality_list in
                        equality_classes.values()]
    canonical_state_ids = set([s.pk for s in unmatched_states])
    noncanonical_states = [u for u in unmatched_states if u.pk not in canonical_state_ids]

    return (canonical_states, noncanonical_states)


class EquivalencePartitioner(object):

    @classmethod
    def makeDefaultStateEquivalence(kls, equivalence_type):
        if equivalence_type == PropertyState:
            return kls.makePropertyStateEquivalence()
        elif equivalence_type == TaxLotState:
            return kls.makeTaxLotStateEquivalence()
        else:
            raise ValueError(
                "Type '{}' does not have a default state equivalence set.".format(equivalence_type))

    @staticmethod
    def makeCanonicalKeyCalculationFunction(list_of_fieldlists):
        # The official key can only come from the first field in the
        # list.
        canonical_fields = [fieldlist[0] for fieldlist in list_of_fieldlists]
        return (lambda obj: tuple([getattr(obj, field) for field in canonical_fields]))

    @classmethod
    def makeResolvedKeyCalculationFunction(kls, list_of_fieldlists):
        # This "resolves" the object to the best potential value in
        # each field.
        return (lambda obj: tuple(
            [kls._getResolvedValueFromObject(obj, list_of_fields) for list_of_fields in
             list_of_fieldlists]))

    @staticmethod
    def _getResolvedValueFromObject(obj, list_of_fields):
        for field in list_of_fields:
            val = getattr(obj, field)
            if val:
                return val
        else:
            return None

    @staticmethod
    def makeKeyEquivalenceFunction(list_of_fields):
        def cmp(key1, key2):
            for key1_value, key2_value in zip(key1, key2):
                if key1_value == key2_value and key1_value is not None:
                    return True
            else:
                return False

        return cmp

    @staticmethod
    def calculate_key_equivalence(key1, key2):
        for key1_value, key2_value in zip(key1, key2):
            if key1_value == key2_value and key1_value is not None:
                return True
        else:
            return False

    @classmethod
    def makePropertyStateEquivalence(kls):
        property_equivalence_fields = [("pm_property_id", "custom_id_1"),
                                       ("custom_id_1",),
                                       ("normalized_address",)]
        return kls(property_equivalence_fields)

    @classmethod
    def makeTaxLotStateEquivalence(kls):
        tax_lot_equivalence_fields = [("jurisdiction_tax_lot_id", "custom_id_1"),
                                      ("custom_id_1",),
                                      ("normalized_address",)]
        return kls(tax_lot_equivalence_fields)

    def __init__(self, equivalence_class_description):
        # self.equiv_compare_func = self.makeKeyEquivalenceFunction(equivalence_class_description)
        self.equiv_comparison_key_func = self.makeResolvedKeyCalculationFunction(
            equivalence_class_description)
        self.equiv_canonical_key_func = self.makeCanonicalKeyCalculationFunction(
            equivalence_class_description)
        return

    def calculate_comparison_key(self, obj):
        return self.equiv_comparison_key_func(obj)

    def calculate_canonical_key(self, obj):
        return self.equiv_canonical_key_func(obj)

    # def calculate_object_equivalence(self, key, obj):
    #     return self.equiv_compare_func(key, obj)

    def key_needs_merging(self, original_key, new_key):
        return True in [not a and b for (a, b) in zip(original_key, new_key)]

    def merge_keys(self, key1, key2):
        return [a if a else b for (a, b) in zip(key1, key2)]

    def calculate_equivalence_classes(self, list_of_obj):
        # TODO: Finish writing the equivalence class code.

        equivalence_classes = collections.defaultdict(list)

        # There is some subtlety with whether we use "comparison" keys
        # or "canonical" keys.  This reflects the difference between
        # searching vs. deciding information is official.

        # For example, if we are trying to match on pm_property_id is,
        # we may look in either pm_property_id or custom_id_1.  But if
        # we are trying to ask what the pm_property_id of a State is
        # that has a blank pm_property, we would not want to say the
        # value in the custom_id must be the pm_property_id.
        for (ndx, obj) in enumerate(list_of_obj):
            cmp_key = self.calculate_comparison_key(obj)
            can_key = self.calculate_canonical_key(obj)

            for class_key in equivalence_classes:
                if self.calculate_key_equivalence(class_key, cmp_key):
                    equivalence_classes[class_key].append(ndx)

                    if self.key_needs_merging(class_key, cmp_key):
                        merged_key = self.merge_keys(class_key, cmp_key)
                        equivalence_classes[merged_key] = equivalence_classes.pop(class_key)
                    break
            else:
                equivalence_classes[can_key].append(ndx)
        return equivalence_classes  # TODO: Make sure return is correct on this.


def match_and_merge_unmatched_objects(unmatched_states, partitioner, org, import_file):
    """Take a list of unmatched_property_states or
    unmatched_tax_lot_states and returns a set of states that
    correspond to unmatched states."""

    # current_match_cycle = import_file.cycle
    # current_match_cycle = Cycle.objects.filter(organization = org).order_by('-start').first()

    # This removes any states that are duplicates,
    equivalence_classes = partitioner.calculate_equivalence_classes(unmatched_states)

    # For each of the equivalence classes, merge them down to a single
    # object of that type.
    merged_objects = []

    for (class_key, class_ndxs) in equivalence_classes.items():
        if len(class_ndxs) == 1:
            merged_objects.append(unmatched_states[class_ndxs[0]])
            continue

        unmatched_state_class = [unmatched_states[ndx] for ndx in class_ndxs]
        merged_result = unmatched_state_class[0]
        for unmatched in unmatched_state_class[1:]:
            merged_result, changes = save_state_match(merged_result,
                                                      unmatched,
                                                      confidence=0.9,
                                                      match_type=SYSTEM_MATCH,
                                                      user=import_file.import_record.owner
                                                      # What does this param do?
                                                      # default_pk=unmatched_property_states.pk
                                                      )

        else:
            merged_objects.append(merged_result)

    return merged_objects, equivalence_classes.keys()


def merge_unmatched_into_views(unmatched_states, partitioner, org, import_file):
    # This is fairly inefficient, because we grab all the
    # organization's entire PropertyViews at once.  Surely this can be
    # improved, but the logic is unusual/particularly dynamic here, so
    # hopefully this can be refactored into a better, purely database
    # approach... Perhaps existing_view_states can wrap database
    # calls. Still the abstractions are subtly different (can I
    # refactor the partitioner to use Query objects); it may require a
    # bit of thinking.

    current_match_cycle = import_file.cycle
    # current_match_cycle = Cycle.objects.filter(organization = org).order_by('-start').first()

    if isinstance(unmatched_states[0], PropertyState):
        ObjectViewClass = PropertyView
        ParentAttrName = "property"
    elif isinstance(unmatched_states[0], TaxLotState):
        ObjectViewClass = TaxLotView
        ParentAttrName = "tax_lot"
    else:
        raise ValueError("Unknown class '{}' passed to merge_unmatched_into_views".format(
            type(unmatched_states[0])))

    class_views = ObjectViewClass.objects.filter(state__organization=org).select_related('state')
    existing_view_states = collections.defaultdict(dict)
    for view in class_views:
        equivalence_can_key = partitioner.calculate_canonical_key(view.state)
        existing_view_states[equivalence_can_key][view.cycle] = view

    matched_views = []

    for unmatched in unmatched_states:
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

                    merged_state, change_ = save_state_match(current_state,
                                                             unmatched,
                                                             confidence=1.0,
                                                             match_type=SYSTEM_MATCH,
                                                             user=import_file.import_record.owner)

                    current_view.state = merged_state
                    current_view.save()
                    matched_views.append(current_view)
                else:
                    # Grab another view that has the same parent as
                    # the one we belong to.
                    cousin_view = existing_view_states[key].values()[0].values()[0][0]
                    view_parent = getattr(cousin_view, ParentAttrName)
                    new_view = type(cousin_view)()
                    setattr(new_view, ParentAttrName, view_parent)
                    new_view.save()
                    matched_views.append(new_view)

                break
        else:
            # Create a new object/view for the current object.
            created_view = unmatched.promote(current_match_cycle)
            matched_views.append(created_view)

    return list(set(matched_views))


@shared_task
@lock_and_track
def _match_properties_and_taxlots(file_pk, user_pk):
    import_file = ImportFile.objects.get(pk=file_pk)
    prog_key = get_prog_key('match_buildings', file_pk)
    org = Organization.objects.filter(users=import_file.import_record.owner).first()

    # Return a list of all the properties/tax lots based on the import file.
    all_unmatched_properties = import_file.find_unmatched_property_states()
    if all_unmatched_properties:

        # Filter out the duplicates.  Do we actually want to delete them
        # here?  Mark their abandonment in the Audit Logs?
        unmatched_properties, duplicate_property_states = filter_duplicated_states(
            all_unmatched_properties)

        property_partitioner = EquivalencePartitioner.makeDefaultStateEquivalence(PropertyState)

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner.
        unmatched_properties, property_equivalence_keys = match_and_merge_unmatched_objects(
            unmatched_properties,
            property_partitioner, org,
            import_file)

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        merged_property_views = merge_unmatched_into_views(unmatched_properties,
                                                           property_partitioner, org, import_file)
    else:
        duplicate_property_states = []
        merged_property_views = []

    # Do the same process with the TaxLots.
    all_unmatched_tax_lots = import_file.find_unmatched_tax_lot_states()
    if all_unmatched_tax_lots:
        unmatched_tax_lots, duplicate_tax_lot_states = filter_duplicated_states(
            all_unmatched_tax_lots)

        taxlot_partitioner = EquivalencePartitioner.makeDefaultStateEquivalence(TaxLotState)

        unmatched_tax_lots, taxlot_equivalence_keys = match_and_merge_unmatched_objects(
            unmatched_tax_lots,
            taxlot_partitioner, org,
            import_file)

        merged_taxlot_views = merge_unmatched_into_views(unmatched_tax_lots, taxlot_partitioner,
                                                         org, import_file)
    else:
        duplicate_tax_lot_states = []
        merged_taxlot_views = []

    pair_new_states(merged_property_views, merged_taxlot_views)

    # Mark all the unmatched objects as done with matching and mapping
    # There should be some kind of bulk-update/save thing we can do to
    # improve upon this.
    for state in chain(all_unmatched_properties, all_unmatched_tax_lots):
        state.data_state = DATA_STATE_MATCHING
        state.save()

    for state in map(lambda x: x.state, chain(merged_taxlot_views, merged_property_views)):
        state.data_state = DATA_STATE_MATCHING
        state.save()

    for state in chain(duplicate_property_states, duplicate_tax_lot_states):
        state.data_state = DATA_STATE_DELETE
        state.save()

    # This is a kind of vestigial code that I do not particularly understand.
    import_file.mapping_completion = 0
    import_file.save()

    return _finish_matching(import_file, prog_key)


@shared_task
@lock_and_track
def _remap_data(import_file_pk):
    """The delicate parts of deleting and remapping data for a file.
    Deprecate this method and integrate the "delicate parts" of this into map_data.

    :param import_file_pk: int, the ImportFile primary key.
    :param mapping_cache_key: str, the cache key for this file's mapping prog.

    """
    # Reset mapping progress cache as well.
    import_file = ImportFile.objects.get(pk=import_file_pk)

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

    import_file.mapping_done = False
    import_file.mapping_completion = None
    import_file.save()

    map_data(import_file_pk)


@shared_task
def remap_data(import_file_pk):
    """"Delete mapped buildings for current import file, re-map them."""
    import_file = ImportFile.objects.get(pk=import_file_pk)
    # Check to ensure that the building has not already been merged.
    mapping_cache_key = get_prog_key('map_data', import_file.pk)
    if import_file.matching_done or import_file.matching_completion:
        result = {
            'status': 'warning',
            'progress': 100,
            'message': 'Mapped buildings already merged',
            'progress_key': mapping_cache_key
        }
        set_cache(mapping_cache_key, result['status'], result)
        return result

    # Make sure that our mapping cache progress is reset.
    result = {
        'status': 'success',
        'progress': 0,
        'message': 'Initializing mapping cache',
        'progress_key': mapping_cache_key
    }
    set_cache(mapping_cache_key, result['status'], result)

    _remap_data.delay(import_file_pk)

    result = get_cache(mapping_cache_key)
    return result


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

    :param properties: QuerySet of PropertyStates
    :param pm_id:
    :param tax_id:
    :param custom_id:
    :return:
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

    matches = properties.filter(reduce(operator.or_, params))

    return matches


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


def save_state_match(state1, state2, confidence=None, user=None,
                     match_type=None, default_match=None, import_filename=None):
    from seed.lib.merging import merging as seed_merger

    merged_state = type(state1).objects.create(organization=state1.organization)
    merged_state, changes = seed_merger.merge_state(merged_state,
                                                    state1, state2,
                                                    seed_merger.get_state_attrs([state1, state2]),
                                                    conf=confidence,
                                                    default=state2,
                                                    match_type=SYSTEM_MATCH)

    AuditLogClass = PropertyAuditLog if isinstance(merged_state, PropertyState) else TaxLotAuditLog

    assert AuditLogClass.objects.filter(state=state1).count() >= 1
    assert AuditLogClass.objects.filter(state=state2).count() >= 1

    state_1_audit_log = AuditLogClass.objects.filter(state=state1).first()
    state_2_audit_log = AuditLogClass.objects.filter(state=state2).first()

    AuditLogClass.objects.create(organization=state1.organization,
                                 parent1=state_1_audit_log,
                                 parent2=state_2_audit_log,
                                 state=merged_state,
                                 name='System Match',
                                 description='Automatic Merge',
                                 import_filename=import_filename,
                                 record_type=AUDIT_IMPORT)

    # print "merging two properties {}/{}".format(ps1_pk, ps2_pk)
    # pp(ps1)
    # pp(ps2)
    # pp(merged_property_state)

    merged_state.save()

    return merged_state, False


def pair_new_states(merged_property_views, merged_taxlot_views):
    if not merged_property_views and not merged_taxlot_views:
        return

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

    taxlot_m2m_keygen = EquivalencePartitioner(tax_cmp_fmt)
    property_m2m_keygen = EquivalencePartitioner(prop_cmp_fmt)

    import time
    st = time.time()
    property_views = PropertyView.objects.filter(state__organization=org, cycle=cycle).values_list(
        *prop_comparison_field_names)
    taxlot_views = TaxLotView.objects.filter(state__organization=org, cycle=cycle).values_list(
        *tax_comparison_field_names)

    et = time.time()
    print "{} seconds.".format(et - st)

    # For each of the view objects, make an
    prop_type = namedtuple("Prop", prop_comparison_fields)
    taxlot_type = namedtuple("TL", tax_comparison_fields)

    # Makes object with field_name->val attributes on them.
    property_objects = [prop_type(*attr) for attr in property_views]
    taxlot_objects = [taxlot_type(*attr) for attr in taxlot_views]

    # TODO: I believe this is incorrect, but doing this for simplicity
    # now. The logic that is being missed is a pretty extreme corner
    # case.

    # TODO: I should generate one key for each property for each thing
    # in it's lot number state.

    # property_keys = {property_m2m_keygen.calculate_comparison_key(p): p.pk for p in property_objects}
    # taxlot_keys = [taxlot_m2m_keygen.calculate_comparison_key(tl): tl.pk for tl in taxlot_objects}

    # Calculate a key for each of the split fields.
    property_keys_orig = dict(
        [(property_m2m_keygen.calculate_comparison_key(p), p.pk) for p in property_objects])

    # property_keys = copy.deepcopy(property_keys_orig)

    # TODO: Refactor this somehow
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
    print "Done"
    taxlot_keys = dict(
        [(taxlot_m2m_keygen.calculate_comparison_key(p), p.pk) for p in taxlot_objects])

    # property_comparison_keys = {property_m2m_keygen.calculate_comparison_key_key(p): p.pk for p in property_objects}
    # property_canonical_keys = {property_m2m_keygen.calculate_canonical_key(p): p.pk for p in property_objects}

    possible_merges = []  # List of prop.id, tl.id merges.

    for pv in merged_property_views:
        # if pv.state.lot_number and ";" in pv.state.lot_number:
        #     pdb.set_trace()

        pv_key = property_m2m_keygen.calculate_comparison_key(pv.state)
        # TODO: Refactor pronto.  This iterating over the tax lot is totally bogus and I hate it.
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

    print "Found {} merges".format(len(possible_merges))
    for m2m in set(possible_merges):
        pv_pk, tlv_pk = m2m
        pv = PropertyView.objects.get(pk=pv_pk)
        tlv = TaxLotView.objects.get(pk=tlv_pk)

        connection = TaxLotProperty.objects.filter(property_view_id=pv_pk,
                                                   taxlot_view_id=tlv_pk).count()
        if connection:
            continue

        is_primary = TaxLotProperty.objects.filter(property_view_id=pv_pk).count() == 0

        m2m_join = TaxLotProperty(property_view_id=pv_pk, taxlot_view_id=tlv_pk, cycle=cycle,
                                  primary=is_primary)
        m2m_join.save()

    print "Done with JOIN CODE"
    return
