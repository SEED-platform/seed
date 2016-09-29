# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import

import datetime
import operator
import re
import string
import time
import traceback
from _csv import Error
from functools import reduce

import usaddress
from celery import chord
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.db.models import Q
from streetaddress import StreetAddressFormatter

from seed.audit_logs.models import AuditLog
from seed.cleansing.models import Cleansing
from seed.cleansing.tasks import (
    finish_cleansing,
    cleanse_data_chunk,
)
from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
    STATUS_READY_TO_MERGE,
    ROW_DELIMITER,
    DuplicateDataError,
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
    BS_VALUES_LIST,
    GREEN_BUTTON_BS,
    GREEN_BUTTON_RAW,
    PORTFOLIO_BS,
    PORTFOLIO_RAW,
    POSSIBLE_MATCH,
    SYSTEM_MATCH,
    Column,
    ColumnMapping,
    find_canonical_building_values,
    initialize_canonical_building,
    save_snapshot_match,
    BuildingSnapshot,
    PropertyState,
    PropertyView,
    TaxLotState,
    DATA_STATE_IMPORT,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
)
from seed.utils.buildings import get_source_type
from seed.utils.cache import set_cache, increment_cache, get_cache

logger = get_task_logger(__name__)

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


def _normalize_tax_lot_id(value):
    return value.strip().lstrip('0').upper().replace(
        '-', ''
    ).replace(
        ' ', ''
    ).replace(
        '/', ''
    ).replace(
        '\\', ''
    )


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

    logger.debug("Mapping row chunks")
    import_file = ImportFile.objects.get(pk=file_pk)
    save_type = PORTFOLIO_BS
    if source_type == ASSESSED_RAW:
        save_type = ASSESSED_BS

    org = Organization.objects.get(pk=import_file.import_record.super_organization.pk)

    table_mappings = ColumnMapping.get_column_mappings_by_table_name(org)
    logger.debug("Mappings are %s" % table_mappings)
    map_cleaner = _build_cleaner(org)

    # yes, there are three cascading for loops here. sorry :(
    md = MappingData()
    for table, mappings in table_mappings.iteritems():
        # This may be historic, but we need to pull out the extra_data_fields here to pass into
        # mapper.map_row. apply_columns are extra_data columns (the raw column names)
        extra_data_fields = []
        for k, v in mappings.iteritems():
            if not md.find_column(v[0], v[1]):
                extra_data_fields.append(k)
        logger.debug("extra data fields: {}".format(extra_data_fields))
        logger.debug("table {} has the maps: {}".format(table, mappings))
        # All the data live in the PropertyState.extra_data field when the data are imported
        data = PropertyState.objects.filter(id__in=ids).only('extra_data').iterator()

        # figure out which import field is defined as the unique field that may have a delimiter of
        # individual values (e.g. tax lot ids). The definition of the delimited field is currently
        # hard coded
        try:
            delimited_field = mappings.keys()[
                mappings.values().index(('TaxLotState', 'jurisdiction_tax_lot_id'))]
        except ValueError:
            delimited_field = None
            # field does not exist in mapping list, so ignoring

        logger.debug("my delimited_field is {}".format(delimited_field))

        # TODO: we probably need a way to allow for certain fields to be imported into all tables.
        # for example the jurisdiction_tax_lot_id is useful on propertystate.extra_data too.

        # Since we are importing CSV, then each extra_data field will have the same fields. So
        # save the map_model_obj outside of for loop to pass into the `save_column_names` methods
        map_model_obj = None

        # Loop over all the rows
        for original_row in data:

            # expand the row into multiple rows if needed with the delimited_field replaced with a
            # single value. This minimizes the need to rewrite the downstream code.
            # Weeee... the data are in the extra_data column.
            for row in expand_rows(original_row.extra_data, delimited_field):

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

                # Assign some other arguments here
                map_model_obj.import_file = import_file
                map_model_obj.source_type = save_type
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
                    logger.debug("recent_sale_date was an empty string, setting to None")
                    map_model_obj.recent_sale_date = None
                if hasattr(map_model_obj,
                           'generation_date') and map_model_obj.generation_date == '':
                    logger.debug("generation_date was an empty string, setting to None")
                    map_model_obj.generation_date = None
                if hasattr(map_model_obj, 'release_date') and map_model_obj.release_date == '':
                    logger.debug("release_date was an empty string, setting to None")
                    map_model_obj.release_date = None
                if hasattr(map_model_obj, 'year_ending') and map_model_obj.year_ending == '':
                    logger.debug("year_ending was an empty string, setting to None")
                    map_model_obj.year_ending = None
                # --- END TEMP HACK ----

                # There is a potential thread safe issue here:
                # This method is called in parallel on production systems, so we need to make
                # sure that the object hasn't already been created.
                # For example, in the test data the tax lot id is the same for many rows. Make sure
                # to only create/save the object if it hasn't been created before.
                map_model_obj.save()

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
    logger.debug("Starting to map the data")
    prog_key = get_prog_key('map_data', file_pk)
    import_file = ImportFile.objects.get(pk=file_pk)
    # Don't perform this task if it's already been completed.
    if import_file.mapping_done:
        logger.debug("_map_data mapping_done is true")
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
        logger.debug("_map_data raw_save_done is false, queueing the task until raw_save finishes")
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
        logger.debug("Not creating finish_mapping chord, calling directly")
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


@shared_task
def _save_raw_data_chunk(chunk, file_pk, prog_key, increment, *args, **kwargs):
    """Save the raw data to the database."""
    import_file = ImportFile.objects.get(pk=file_pk)

    # Save our "column headers" and sample rows for F/E.
    source_type = get_source_type(import_file)
    for c in chunk:
        raw_property = PropertyState()
        raw_property.import_file = import_file  # not defined in new data model
        raw_property.extra_data = c
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
    logger.debug('Returning from _save_raw_data_chunk')

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
    logger.debug('Returning from finish_raw_save')
    return result


def cache_first_rows(import_file, parser):
    """Cache headers, and rows 2-6 for validation/viewing.

    :param import_file: ImportFile inst.
    :param parser: unicode-csv.Reader instance.

    Unfortunately, this is duplicated logic from data_importer,
    but since data_importer makes many faulty assumptions we need to do
    it differently.

    """
    parser.seek_to_beginning()
    rows = parser.next()

    validation_rows = []
    for i in range(5):
        try:
            row = rows.next()
            if row:
                validation_rows.append(row)
        except StopIteration:
            """Less than 5 rows in file"""
            break

    # return the first row of the headers which are cleaned
    first_row = parser.headers()

    tmp = []
    for r in validation_rows:
        tmp.append(ROW_DELIMITER.join([str(r[x]) for x in first_row]))

    import_file.cached_second_to_fifth_row = "\n".join(tmp)

    if first_row:
        first_row = ROW_DELIMITER.join(first_row)
    import_file.cached_first_row = first_row or ''

    import_file.save()

    # Reset our file pointer for mapping.
    parser.seek_to_beginning()


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
    logger.debug("Current cache state")
    current_cache = get_cache(prog_key)
    logger.debug(current_cache)
    time.sleep(2)  # NL: yuck
    result = current_cache

    try:
        logger.debug('Attempting to access import_file')
        import_file = ImportFile.objects.get(pk=file_pk)
        if import_file.raw_save_done:
            result['status'] = 'warning'
            result['message'] = 'Raw data already saved'
            result['progress'] = 100
            set_cache(prog_key, result['status'], result)
            logger.debug('Returning with warn from _save_raw_data')
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

        logger.debug('Appended all tasks')
        import_file.save()
        logger.debug('Saved import_file')

        if tasks:
            logger.debug('Adding chord to queue')
            chord(tasks, interval=15)(finish_raw_save.si(file_pk))
        else:
            logger.debug('Skipped chord')
            finish_raw_save.s(file_pk)

        logger.debug('Finished raw save tasks')
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
    logger.debug('Returning from end of _save_raw_data with state:')
    logger.debug(result)
    return result


@shared_task
@lock_and_track
def save_raw_data(file_pk, *args, **kwargs):
    logger.debug('In save_raw_data')

    prog_key = get_prog_key('save_raw_data', file_pk)
    initializing_key = {
        'status': 'not-started',
        'progress': 0,
        'progress_key': prog_key
    }
    set_cache(prog_key, initializing_key['status'], initializing_key)
    _save_raw_data.delay(file_pk, *args, **kwargs)
    logger.debug('Returning from save_raw_data')
    result = get_cache(prog_key)
    return result


# TODO: Not used -- remove
def _stringify(values):
    """Take iterable of str and NoneTypes and reduce to space sep. str."""
    return ' '.join(
        [PUNCT_REGEX.sub('', value.lower()) for value in values if value]
    )


def handle_results(results, b_idx, can_rev_idx, unmatched_list, user_pk):
    """Seek IDs and save our snapshot match.

    :param results: list of tuples. [('match', 0.99999),...]
    :param b_idx: int, the index of the current building in the unmatched_list.
    :param can_rev_idx: dict, reverse index from match -> canonical PK.
    :param user_pk: user ID, used for AuditLog logging
    :unmatched_list: list of dicts, the result of a values_list query for
        unmatched PropertyState.

    """
    match_string, confidence = results[0]  # We always care about closest match
    match_type = SYSTEM_MATCH
    # If we passed the minimum threshold, we're here, but we need to
    # distinguish probable matches from good matches.
    if confidence < getattr(settings, 'MATCH_MED_THRESHOLD', 0.7):
        match_type = POSSIBLE_MATCH

    can_snap_pk = can_rev_idx[match_string]
    building_pk = unmatched_list[b_idx][0]  # First element is PK

    bs, changes = save_snapshot_match(
        can_snap_pk,
        building_pk,
        confidence=confidence,
        match_type=match_type,
        default_pk=building_pk,
    )
    canon = bs.canonical_building
    action_note = 'System matched building.'
    if changes:
        action_note += "  Fields changed in cannonical building:\n"
        for change in changes:
            action_note += "\t{field}:\t".format(
                field=change["field"].replace("_", " ").replace("-",
                                                                "").capitalize(),
            )
            if "from" in change:
                action_note += "From:\t{prev}\tTo:\t".format(
                    prev=change["from"])

            action_note += "{value}\n".format(value=change["to"])
        action_note = action_note[:-1]
    AuditLog.objects.create(
        user_id=user_pk,
        content_object=canon,
        action_note=action_note,
        action='save_system_match',
        organization=bs.super_organization,
    )


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

    _match_buildings.delay(file_pk, user_pk)

    return {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }


def handle_id_matches(unmatched_bs, test_property, import_file, user_pk):
    """
    Deals with exact matches in the IDs of buildings.

    :param unmatched_bs:
    :param test_property:
    :param import_file:
    :param user_pk:
    :return:
    """

    # TODO: this only works for PropertyStates right now because the unmatched_bs is a QuerySet
    # of PropertyState of which have the .pm_property_id and .custom_id_1 fields.
    id_matches = query_property_matches(
        unmatched_bs,
        test_property.pm_property_id,
        test_property.custom_id_1
    )
    if not id_matches.exists():
        return

    # Check to see if there are any duplicates here
    for match in id_matches:
        if is_same_snapshot(unmatched_bs, match):
            raise DuplicateDataError(match.pk)

    # merge save as system match with high confidence.
    for match in id_matches:
        # Merge all matches together; updating "unmatched" pointer as we go.
        unmatched_bs, changes = save_snapshot_match(
            match.pk,
            unmatched_bs.pk,
            confidence=0.9,
            match_type=SYSTEM_MATCH,
            # TODO: we should and probably can remove this field, please :D
            user=import_file.import_record.owner,
            default_pk=unmatched_bs.pk
        )
        canon = unmatched_bs.canonical_building
        canon.canonical_snapshot = unmatched_bs
        canon.save()
        action_note = 'System matched building ID.'
        if changes:
            action_note += "  Fields changed in canonical building:\n"
            for change in changes:
                action_note += "\t{field}:\t".format(
                    field=change["field"].replace("_", " ").replace("-",
                                                                    "").capitalize())
                if "from" in change:
                    action_note += "From:\t{prev}\tTo:\t".format(
                        prev=change["from"])

                action_note += "{value}\n".format(value=change["to"])
            action_note = action_note[:-1]

        AuditLog.objects.create(
            user_id=user_pk,
            content_object=canon,
            action_note=action_note,
            action='save_system_match',
            organization=unmatched_bs.super_organization,
        )

    # Returns the most recent child of all merging.
    return unmatched_bs


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


def _normalize_address_direction(direction):
    direction = direction.lower().replace('.', '')
    direction_map = {
        'east': 'e',
        'west': 'w',
        'north': 'n',
        'south': 's',
        'northeast': 'ne',
        'northwest': 'nw',
        'southeast': 'se',
        'southwest': 'sw'
    }
    if direction in direction_map:
        return direction_map[direction]
    return direction


POST_TYPE_MAP = {
    'avenue': 'ave',
}


def _normalize_address_post_type(post_type):
    value = post_type.lower().replace('.', '')
    return POST_TYPE_MAP.get(value, value)


ADDRESS_NUMBER_RE = re.compile((
    r''
    r'(?P<start>[0-9]+)'  # The left part of the range
    r'\s?'  # Optional whitespace before the separator
    r'[\\/-]?'  # Optional Separator
    r'\s?'  # Optional whitespace after the separator
    r'(?<=[\s\\/-])'  # Enforce match of at least one separator char.
    r'(?P<end>[0-9]+)'  # THe right part of the range
))


def _normalize_address_number(address_number):
    """
    Given the numeric portion of an address, normalize it.
    - strip leading zeros from numbers.
    - remove whitespace from ranges.
    - convert ranges to use dash as separator.
    - expand any numbers that appear to have had their leading digits
      truncated.
    """
    match = ADDRESS_NUMBER_RE.match(address_number)
    if match:
        # This address number is a range, so normalize it.
        components = match.groupdict()
        range_start = components['start'].lstrip("0")
        range_end = components['end'].lstrip("0")
        if len(range_end) < len(range_start):
            # The end range value is omitting a common prefix.  Add it back.
            prefix_length = len(range_start) - len(range_end)
            range_end = range_start[:prefix_length] + range_end
        return '-'.join([range_start, range_end])

    # some addresses have leading zeros, strip them here
    return address_number.lstrip("0")


def _normalize_address_str(address_val):
    """
    Normalize the address to conform to short abbreviations.

    If an invalid address_val is provided, None is returned.

    If a valid address is provided, a normalized version is returned.
    """

    # if this string is empty the regular expression in the sa wont
    # like it, and fail, so leave returning nothing
    if not address_val:
        return None

    address_val = unicode(address_val).encode('utf-8')

    # Do some string replacements to remove odd characters that we come across
    replacements = {
        '\xef\xbf\xbd': '',
        '\uFFFD': '',
    }
    for k, v in replacements.items():
        address_val = address_val.replace(k, v)

    # now parse the address into number, street name and street type
    try:
        addr = usaddress.tag(str(address_val))[0]
    except usaddress.RepeatedLabelError:
        # usaddress can't parse this at all
        normalized_address = str(address_val)
    except UnicodeEncodeError:
        # Some kind of odd character issue that we aren't handling yet.
        normalized_address = str(address_val)
    else:
        # Address can be parsed, so let's format it.
        normalized_address = ''

        if 'AddressNumber' in addr and addr['AddressNumber'] is not None:
            normalized_address = _normalize_address_number(
                addr['AddressNumber'])

        if 'StreetNamePreDirectional' in addr and addr[
                'StreetNamePreDirectional'] is not None:
            normalized_address = normalized_address + ' ' + _normalize_address_direction(
                addr['StreetNamePreDirectional'])  # NOQA

        if 'StreetName' in addr and addr['StreetName'] is not None:
            normalized_address = normalized_address + ' ' + addr['StreetName']

        if 'StreetNamePostType' in addr and addr[
                'StreetNamePostType'] is not None:
            # remove any periods from abbreviations
            normalized_address = normalized_address + ' ' + _normalize_address_post_type(
                addr['StreetNamePostType'])  # NOQA

        if 'StreetNamePostDirectional' in addr and addr[
                'StreetNamePostDirectional'] is not None:
            normalized_address = normalized_address + ' ' + _normalize_address_direction(
                addr['StreetNamePostDirectional'])  # NOQA

        formatter = StreetAddressFormatter()
        normalized_address = formatter.abbrev_street_avenue_etc(
            normalized_address)

    return normalized_address.lower().strip()


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


@shared_task
@lock_and_track
def _match_buildings(file_pk, user_pk):
    """ngram search against all of the propertystates for org."""
    import_file = ImportFile.objects.get(pk=file_pk)
    prog_key = get_prog_key('match_buildings', file_pk)
    org = Organization.objects.filter(users=import_file.import_record.owner).first()

    # Return a list of all the properties based on the import file
    unmatched_buildings = import_file.find_unmatched_property_states()

    # TODO: need to also return the taxlots
    duplicates = []
    newly_matched_building_pks = []

    # Filter out matches based on ID.
    # if the match is a duplicate of other existing data add it to a list
    # and indicate which existing record it is a duplicate of
    for unmatched in unmatched_buildings:
        # print "trying to match %s" % unmatched.__dict__
        try:
            match = handle_id_matches(unmatched_buildings, unmatched, import_file, user_pk)
            # print "My match was %s" % match
        except DuplicateDataError as e:
            duplicates.append(unmatched.pk)
            unmatched.duplicate_id = e.id
            unmatched.save()
            continue

        if match:
            newly_matched_building_pks.extend([match.pk, unmatched.pk])

    # Remove any buildings we just did exact ID matches with.
    unmatched_buildings = unmatched_buildings.exclude(
        pk__in=newly_matched_building_pks).values_list(*BS_VALUES_LIST)

    # If we don't find any unmatched buildings, there's nothing left to do.
    if not unmatched_buildings:
        _finish_matching(import_file, prog_key)
        return

    # here we deal with duplicates
    unmatched_buildings = unmatched_buildings.exclude(pk__in=duplicates, ).values_list(
        *BS_VALUES_LIST)
    if not unmatched_buildings:
        _finish_matching(import_file, prog_key)
        return

    # here we are going to normalize the addresses to match on address_1
    # field, this is not ideal because you could match on two locations
    # with same address_1 but different city
    unmatched_normalized_addresses = [
        _normalize_address_str(unmatched[4]) for unmatched in
        unmatched_buildings
    ]

    # Here we want all the values not related to the BS id for doing comps.
    # dont do this now
    #     unmatched_ngrams = [
    #         _stringify(list(values)[1:]) for values in unmatched_buildings
    #     ]

    canonical_buildings = find_canonical_building_values(org)
    if not canonical_buildings:
        # There are no canonical_buildings for this organization, all unmatched
        # buildings will then become canonicalized.
        hydrated_unmatched_buildings = BuildingSnapshot.objects.filter(
            pk__in=[item[0] for item in unmatched_buildings]
        )
        num_unmatched = len(unmatched_normalized_addresses) or 1
        increment = 1.0 / num_unmatched * 100
        for (i, unmatched) in enumerate(hydrated_unmatched_buildings):
            initialize_canonical_building(unmatched, user_pk)
            if i % 100 == 0:
                increment_cache(prog_key, increment * 100)

        _finish_matching(import_file, prog_key)
        return

    # This allows us to retrieve the PK for a given NGram after a match.
    can_rev_idx = {
        _normalize_address_str(value[4]): value[0] for value in
        canonical_buildings
    }
    # (SD) This loads up an ngram object with all the canonical buildings. The
    # values are the lists of identifying data for each building
    #
    # (SD) the stringify is given all but the first item in the values list and
    # it concatenates each item with a space in the middle

    # we no longer need to
    #     n = ngram.NGram(
    #         [_stringify(values[1:]) for values in canonical_buildings]
    #     )
    # here we are going to normalize the addresses to match on address_1 field,
    # this is not ideal because you could match on two locations with same
    # address_1 but different city
    canonical_buildings_addresses = [
        _normalize_address_str(values[4]) for values in canonical_buildings
    ]
    # For progress tracking
    # sd we now use the address
    #    num_unmatched = len(unmatched_ngrams) or 1
    num_unmatched = len(unmatched_normalized_addresses) or 1
    # this code below seemed to be unclear when I was debugging so I added the brackets
    increment = (1.0 / num_unmatched) * 100

    # PKs when we have a match.
    import_file.mapping_completion = 0
    import_file.save()
    # this section spencer changed to make the exact match
    for i, un_m_address in enumerate(unmatched_normalized_addresses):
        # If we have an address, try to match it
        if un_m_address is not None:
            results = _find_matches(un_m_address,
                                    canonical_buildings_addresses)
        else:
            results = []

        if results:
            handle_results(
                results, i, can_rev_idx, unmatched_buildings, user_pk
            )
        else:
            hydrated_building = BuildingSnapshot.objects.get(
                pk=unmatched_buildings[i][0]
            )
            initialize_canonical_building(hydrated_building, user_pk)

        if i % 100 == 0:
            increment_cache(prog_key, increment * 100)
            import_file.mapping_completion += int(increment * 100)
            import_file.save()

    _finish_matching(import_file, prog_key)

    return {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }


@shared_task
@lock_and_track
def _remap_data(import_file_pk):
    """The delicate parts of deleting and remapping data for a file.

    :param import_file_pk: int, the ImportFile primary key.
    :param mapping_cache_key: str, the cache key for this file's mapping prog.

    """
    # Reset mapping progress cache as well.
    import_file = ImportFile.objects.get(pk=import_file_pk)
    # Delete buildings already mapped for this file.
    PropertyState.objects.filter(
        import_file=import_file,
        source_type__in=(ASSESSED_BS, PORTFOLIO_BS, GREEN_BUTTON_BS)
        # TODO: make these not hard coded integers
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
