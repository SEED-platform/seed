# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from __future__ import absolute_import

import collections
import copy
import datetime as dt
import hashlib
import operator
import traceback
from _csv import Error
from collections import namedtuple
from functools import reduce
from itertools import chain

from celery import chord, shared_task
from celery.utils.log import get_task_logger
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from unidecode import unidecode

from seed.data_importer.equivalence_partitioner import EquivalencePartitioner
from seed.data_importer.models import (
    ImportFile,
    ImportRecord,
    STATUS_READY_TO_MERGE,
)
from seed.decorators import lock_and_track
from seed.green_button import xml_importer
from seed.lib.mcm import cleaners, mapper, reader
from seed.lib.mcm.mapper import expand_rows
from seed.lib.mcm.utils import batch
from seed.lib.merging import merging
from seed.lib.progress_data.progress_data import ProgressData
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
    MERGE_STATE_UNKNOWN,
    DATA_STATE_UNKNOWN)
from seed.models import PropertyAuditLog
from seed.models import TaxLotAuditLog
from seed.models import TaxLotProperty
from seed.models.auditlog import AUDIT_IMPORT
from seed.models.data_quality import DataQualityCheck
from seed.utils.buildings import get_source_type

_log = get_task_logger(__name__)

STR_TO_CLASS = {'TaxLotState': TaxLotState, 'PropertyState': PropertyState}


@shared_task(ignore_result=True)
def check_data_chunk(model, ids, dq_id):
    if model == 'PropertyState':
        qs = PropertyState.objects.filter(id__in=ids)
    elif model == 'TaxLotState':
        qs = TaxLotState.objects.filter(id__in=ids)
    else:
        qs = None
    super_org = qs.first().organization

    d = DataQualityCheck.retrieve(super_org.get_parent().id)
    d.check_data(model, qs.iterator())
    d.save_to_cache(dq_id)


@shared_task(ignore_result=True)
def finish_checking(progress_key):
    """
    Chord that is called after the data quality check is complete

    :param identifier: import file primary key
    :return: dict, results from queue
    """
    progress_data = ProgressData.from_key(progress_key)
    progress_data.finish_with_success()
    return progress_data.result()


def do_checks(org_id, propertystate_ids, taxlotstate_ids, import_file_id=None):
    """
    Run the dq checks on the data

    :param org_id:
    :param propertystate_ids:
    :param taxlotstate_ids:
    :param import_file_id: int, if present, find the data to check by the import file id
    :return:
    """
    # If import_file_id, then use that as the identifier, otherwise, initialize_cache will
    # create a new random id
    cache_key, dq_id = DataQualityCheck.initialize_cache(import_file_id)

    progress_data = ProgressData(func_name='check_data', unique_id=dq_id)
    progress_data.delete()

    if import_file_id:
        propertystate_ids = list(
            PropertyState.objects.filter(import_file=import_file_id).exclude(
                data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT,
                                DATA_STATE_DELETE]).values_list('id', flat=True)
        )
        taxlotstate_ids = list(
            TaxLotState.objects.filter(import_file=import_file_id).exclude(
                data_state__in=[DATA_STATE_UNKNOWN, DATA_STATE_IMPORT,
                                DATA_STATE_DELETE]).values_list('id', flat=True)
        )

    tasks = _data_quality_check_create_tasks(
        org_id, propertystate_ids, taxlotstate_ids, dq_id
    )
    progress_data.total = len(tasks)
    progress_data.save()
    if tasks:
        # specify the chord as an immutable with .si
        chord(tasks, interval=15)(finish_checking.si(progress_data.key))
    else:
        finish_checking.s(progress_data.key)

    # always return something so that the code works with always eager
    return progress_data.result()


@shared_task(ignore_result=True)
def finish_mapping(import_file_id, mark_as_done, progress_key):
    import_file = ImportFile.objects.get(pk=import_file_id)
    progress_data = ProgressData.from_key(progress_key)

    # Do not set the mapping_done flag unless mark_as_done is set. This allows an actual
    # user to review the mapping before it is saved and matching starts.
    if mark_as_done:
        import_file.mapping_done = True
        import_file.save()

    # Set all statuses to Done, etc
    states = ('done', 'active', 'queued')
    actions = ('merge_analysis', 'premerge_analysis')

    # Really all these status attributes are tedious.
    import_record = ImportRecord.objects.get(pk=import_file.import_record.pk)
    for action in actions:
        for state in states:
            value = False
            if state == 'done':
                value = True
            setattr(import_record, '{0}_{1}'.format(action, state), value)

    import_record.finish_time = timezone.now()
    import_record.status = STATUS_READY_TO_MERGE
    import_record.save()

    return progress_data.finish_with_success()


def _build_cleaner(org):
    """Return a cleaner instance that knows about a mapping's unit types.

    Basically, this just tells us how to try and cast types during cleaning
    based on the Column definition in the database.

    :param org: organization instance.
    :returns: dict of dicts. {'types': {'col_name': 'type'},}
    """

    def _translate_unit_to_type(unit):
        if unit is None or unit == 'String':
            return 'string'

        return unit.lower()

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


def _build_cleaner_2(org):
    """Return a cleaner instance that knows about a mapping's unit types

    :param org: organization instance
    :returns: cleaner instance

    This tells us how to try to cast types during cleaning, based on the Column
    definition in the database.

    Here we're also dealing with Pint with a tuple 'type' acting as a sort of
    parameterized type like `Pint(SquareMetres)` ... just using `pint` as the
    type doesn't tell the whole story of the type ...  eg. the "type" is
    ('quantity', 'm**2') and the cleaner can dispatch sensibly on this.

    Note that this is generally going to be on the *raw* column. Let's assume
    an example where incoming data has created raw columns 'Gross Building Area
    (m2)' and 'Gross Building Area (ft2)' ...  we'll need to disambiguate a
    mapping to mapped column 'gross_building_area' based on the raw column
    name.
    """

    # start with the predefined types
    ontology = {'types': Column.retrieve_db_types()['types']}

    query_set = Column.objects.filter(organization=org, units_pint__isnull=False)
    for column in query_set:
        # add available pint types as a tuple type
        ontology['types'][column.column_name] = ('quantity', column.units_pint)

    return cleaners.Cleaner(ontology)


@shared_task(ignore_result=True)
def map_row_chunk(ids, file_pk, source_type, prog_key, **kwargs):
    """Does the work of matching a mapping to a source type and saving

    :param ids: list of PropertyState IDs to map.
    :param file_pk: int, the PK for an ImportFile obj.
    :param source_type: int, represented by either ASSESSED_RAW or PORTFOLIO_RAW.
    :param prog_key: string, key of the progress key
    :param increment: double, value by which to increment progress key
    """
    progress_data = ProgressData.from_key(prog_key)
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
        for table, mappings in table_mappings.items():
            for raw_column_name in mappings.keys():
                if raw_column_name not in list_of_raw_columns:
                    del table_mappings[table][raw_column_name]

        # check that the dictionaries are not empty, if empty, then delete.
        for table in table_mappings.keys():
            if not table_mappings[table]:
                del table_mappings[table]

    map_cleaner = _build_cleaner_2(org)

    # *** BREAK OUT INTO SEPARATE METHOD ***
    # figure out which import field is defined as the unique field that may have a delimiter of
    # individual values (e.g. tax lot ids). The definition of the delimited field is currently
    # hard coded
    try:
        delimited_fields = {}
        if 'TaxLotState' in table_mappings.keys():
            tmp = table_mappings['TaxLotState'].keys()[table_mappings['TaxLotState'].values().index(
                ('TaxLotState', 'jurisdiction_tax_lot_id', 'Jurisdiction Tax Lot ID', False))]
            delimited_fields['jurisdiction_tax_lot_id'] = {
                'from_field': tmp,
                'to_table': 'TaxLotState',
                'to_field_name': 'jurisdiction_tax_lot_id',
            }
    except ValueError:
        delimited_fields = {}
        # field does not exist in mapping list, so ignoring

    # _log.debug("my table mappings are {}".format(table_mappings))
    # _log.debug("delimited_field that will be expanded and normalized: {}".format(delimited_fields))

    # If a single file is being imported into both the tax lot and property table, then add
    # an extra custom mapping for the cross-related data. If the data are not being imported into
    # the property table then make sure to skip this so that superfluous property entries are
    # not created.
    if 'PropertyState' in table_mappings.keys():
        if delimited_fields and delimited_fields['jurisdiction_tax_lot_id']:
            table_mappings['PropertyState'][
                delimited_fields['jurisdiction_tax_lot_id']['from_field']] = (
                'PropertyState', 'lot_number', 'Lot Number', False)
    # *** END BREAK OUT ***

    # yes, there are three cascading for loops here. sorry :(
    for table, mappings in table_mappings.items():
        if not table:
            continue

        # This may be historic, but we need to pull out the extra_data_fields here to pass into
        # mapper.map_row. apply_columns are extra_data columns (the raw column names)
        extra_data_fields = []
        for k, v in mappings.items():
            # the 3rd element is the is_extra_data flag. Need to convert this to a dict and not a tuple.
            if v[3]:
                extra_data_fields.append(k)
        # _log.debug("extra data fields: {}".format(extra_data_fields))

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
            for k, d in delimited_fields.items():
                if d['to_table'] == table:
                    expand_row = True
            # _log.debug("Expand row is set to {}".format(expand_row))

            delimited_field_list = []
            for _, v in delimited_fields.items():
                delimited_field_list.append(v['from_field'])

            # _log.debug("delimited_field_list is set to {}".format(delimited_field_list))

            # The raw data upon import is in the extra_data column
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
                if hasattr(map_model_obj, 'clean'):
                    map_model_obj.clean()

                # There is a potential thread safe issue here:
                # This method is called in parallel on production systems, so we need to make
                # sure that the object hasn't already been created.
                # For example, in the test data the tax lot id is the same for many rows. Make sure
                # to only create/save the object if it hasn't been created before.
                if hash_state_object(map_model_obj, include_extra_data=False) == \
                    hash_state_object(STR_TO_CLASS[table](organization=map_model_obj.organization),
                                      include_extra_data=False):
                    # Skip this object as it has no data...
                    _log.warn("Skipping property or taxlot during mapping")
                    continue

                try:
                    # There was an error with a field being too long [> 255 chars].
                    map_model_obj.save()

                    # Create an audit log record for the new map_model_obj that was created.

                    AuditLogClass = PropertyAuditLog if isinstance(
                        map_model_obj, PropertyState) else TaxLotAuditLog
                    AuditLogClass.objects.create(organization=org,
                                                 state=map_model_obj,
                                                 name='Import Creation',
                                                 description='Creation from Import file.',
                                                 import_filename=import_file,
                                                 record_type=AUDIT_IMPORT)

                except ValidationError as e:
                    # Could not save the record for some reason, raise an exception
                    raise Exception(
                        "Unable to save row the model with row {}:{}".format(type(e),
                                                                             e.message))

        # Make sure that we've saved all of the extra_data column names from the first item in list
        if map_model_obj:
            Column.save_column_names(map_model_obj)

    progress_data.step()

    return True


def _map_data_create_tasks(import_file_id, progress_key):
    """
    Get all of the raw data and process it using appropriate mapping.
    @lock_and_track returns a progress_key

    :param import_file_id: int, the id of the import_file we're working with.
    :param mark_as_done: bool, tell finish_mapping that import_file.mapping_done is True
    :return:
    """
    progress_data = ProgressData.from_key(progress_key)
    import_file = ImportFile.objects.get(pk=import_file_id)

    # If we haven't finished saving, we should not proceed with mapping
    # Re-queue this task.
    if not import_file.raw_save_done:
        _log.debug("_map_data raw_save_done is false, queueing the task until raw_save finishes")
        map_data.apply_async(args=[import_file_id], countdown=60, expires=120)
        return progress_data.finish_with_error('waiting for raw data save.')

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

    progress_data.total = len(id_chunks)
    progress_data.save()

    tasks = [map_row_chunk.si(ids, import_file_id, source_type, progress_data.key)
             for ids in id_chunks]

    return tasks


def _data_quality_check_create_tasks(org_id, property_state_ids, taxlot_state_ids, dq_id):
    """
    Entry point into running data quality checks.

    Get the mapped data and run the data_quality class against it in chunks. The
    mapped data are pulled from the PropertyState(or Taxlot) table.

    @lock_and_track returns a progress_key

    :param organization: object, Organization object
    :param property_state_ids: list, list of property state IDs to check
    :param taxlot_state_ids: list, list of tax lot state IDs to check
    :param identifier: str, for retrieving progress status
    """
    # Initialize the data quality checks with the organization here. It is important to do it here
    # since the .retrieve method in the check_data_chunk method will result in a race condition if celery is
    # running in parallel.
    DataQualityCheck.retrieve(org_id)

    tasks = []
    if property_state_ids:
        id_chunks = [[obj for obj in chunk] for chunk in batch(property_state_ids, 100)]
        for ids in id_chunks:
            tasks.append(check_data_chunk.s("PropertyState", ids, dq_id))

    if taxlot_state_ids:
        id_chunks_tl = [[obj for obj in chunk] for chunk in batch(taxlot_state_ids, 100)]
        for ids in id_chunks_tl:
            tasks.append(check_data_chunk.s("TaxLotState", ids, dq_id))

    return tasks


@shared_task(ignore_result=True)
def junk_test(x, y):
    print "now i am here"
    return x * y


def map_data(import_file_id, remap=False, mark_as_done=True):
    """
    Map data task. By default this method will run through the mapping and mark it as complete.
    :param import_file_id: Import File ID
    :param remap: bool, if remapping, then delete previous objects from the database
    :param mark_as_done: bool, if skip review then the mapping_done flag will be set to true at the
    end.
    :return: JSON
    """
    # Clear out the previously mapped data
    DataQualityCheck.initialize_cache(import_file_id)

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
    progress_data = ProgressData(func_name='map_data', unique_id=import_file_id)
    progress_data.delete()

    tasks = _map_data_create_tasks(import_file_id, progress_data.key)
    if tasks:
        chord(tasks)(finish_mapping.si(import_file_id, mark_as_done, progress_data.key))
    else:
        _log.debug("Not creating finish_mapping chord, calling directly")
        finish_mapping.si(import_file_id, mark_as_done, progress_data.key)

    return progress_data.result()


@shared_task(ignore_result=True)
def _save_raw_data_chunk(chunk, file_pk, progress_key):
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
            elif isinstance(v, (dt.datetime, dt.date)):
                raise TypeError("Datetime class not supported in Extra Data. Needs to be a string.")
            else:
                new_chunk[key] = v
        raw_property.extra_data = new_chunk
        raw_property.source_type = source_type
        raw_property.data_state = DATA_STATE_IMPORT

        # We require a save to get our PK
        # We save here to set our initial source PKs.
        raw_property.save()

        super_org = import_file.import_record.super_organization
        raw_property.organization = super_org

        raw_property.save()

    # Indicate progress
    progress_data = ProgressData.from_key(progress_key)
    progress_data.step()

    return True


@shared_task(ignore_result=True)
def finish_raw_save(results, file_pk, progress_key):
    """
    Finish importing the raw file.

    :param results: List of results from the parent task, not really used at the moment
    :param file_pk: ID of the file that was being imported
    :return: results: results from the other tasks before the chord ran
    """
    progress_data = ProgressData.from_key(progress_key)
    import_file = ImportFile.objects.get(pk=file_pk)
    import_file.raw_save_done = True
    import_file.save()

    return progress_data.finish_with_success()


def cache_first_rows(import_file, parser):
    """Cache headers, and rows 2-6 for validation/viewing.

    :param import_file: ImportFile inst.
    :param parser: MCMParser instance.
    """

    # return the first row of the headers which are cleaned
    first_row = parser.headers
    first_five_rows = parser.first_five_rows

    # _log.debug(first_five_rows)

    import_file.cached_second_to_fifth_row = "\n".join(first_five_rows)
    if first_row:
        first_row = reader.ROW_DELIMITER.join(first_row)
    import_file.cached_first_row = first_row or ''
    import_file.save()


@shared_task(ignore_result=True)
@lock_and_track
def _save_raw_green_button_data(file_pk, progress_key):
    """
    Pulls identifying information out of the XML data, find_or_creates
    a building_snapshot for the data, parses and stores the time series
    meter data and associates it with the building snapshot.
    """
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=file_pk)
    import_file.raw_save_done = True
    import_file.save()

    res = xml_importer.import_xml(import_file)

    if res:
        return progress_data.finish_with_success()
    else:
        return progress_data.finish_with_error('data failed to import')


def _save_raw_data_create_tasks(file_pk, progress_key):
    """
    Worker method for saving raw data. Chunk up the CSV or XLSX file and save the raw data
    into the PropertyState table.

    :param file_pk: int, ID of the file to import
    :return: Dict, result from progress data / cache
    """
    progress_data = ProgressData.from_key(progress_key)

    # _log.debug('Attempting to access import_file')
    import_file = ImportFile.objects.get(pk=file_pk)
    if import_file.raw_save_done:
        return progress_data.finish_with_warning('Raw data already saved')

    if import_file.source_type == "Green Button Raw":
        # TODO #239: Should remove green button from here until later.
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
    import_file.save()

    progress_data.total = len(chunks)
    progress_data.save()

    return [_save_raw_data_chunk.s(chunk, file_pk, progress_data.key) for chunk in chunks]


def save_raw_data(file_pk):
    """
    Save the raw data from an imported file. This is the entry point into saving the data.

    :param file_pk: ImportFile Primary Key
    :return: Dict, from cache, containing the progress key to track
    """
    progress_data = ProgressData(func_name='save_raw_data', unique_id=file_pk)
    try:
        # Go get the tasks that need to be created, then call them in the chord here.
        tasks = _save_raw_data_create_tasks(file_pk, progress_data.key)
        if tasks:
            chord(tasks, interval=15)(finish_raw_save.s(file_pk, progress_data.key))
        else:
            finish_raw_save.s(file_pk, progress_data.key)
    except StopIteration:
        progress_data.finish_with_error('StopIteration Exception', traceback.format_exc())
    except Error as e:
        progress_data.finish_with_error('File Content Error: ' + e.message, traceback.format_exc())
    except KeyError as e:
        progress_data.finish_with_error('Invalid Column Name: "' + e.message + '"',
                                        traceback.format_exc())
    except Exception as e:
        progress_data.finish_with_error('Unhandled Error: ' + str(e.message),
                                        traceback.format_exc())
    _log.debug(progress_data.result())
    return progress_data.result()


def match_buildings(file_pk):
    """
    kicks off system matching, returns progress key within the JSON response

    :param file_pk: ImportFile Primary Key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)

    progress_data = ProgressData(func_name='match_buildings', unique_id=file_pk)
    progress_data.delete()

    if import_file.matching_done:
        _log.debug('Matching is already done')
        return progress_data.finish_with_warning('matching already complete')

    if not import_file.mapping_done:
        _log.debug('Mapping is not done yet')
        return progress_data.finish_with_error(
            'Import file is not complete. Retry after mapping is complete', )

    if import_file.cycle is None:
        _log.warn("This should never happen in production")

    # Start, match, pair
    progress_data.total = 3
    progress_data.save()

    data = chord(_match_properties_and_taxlots.s(file_pk, progress_data.key), interval=15)(
        finish_matching.si(file_pk, progress_data.key))


    return progress_data.result()


@shared_task(ignore_result=True)
def finish_matching(import_file_id, progress_key):
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=import_file_id)
    import_file.matching_done = True
    import_file.mapping_completion = 100
    import_file.save()

    return progress_data.finish_with_success()


def hash_state_object(obj, include_extra_data=True):
    def _get_field_from_obj(field_obj, field):
        if not hasattr(field_obj, field):
            return "FOO"  # Return a random value so we can distinguish between this and None.
        else:
            return getattr(field_obj, field)

    m = hashlib.md5()
    for f in Column.retrieve_db_field_name_for_hash_comparison():
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

    # TODO #239: Should we save the hash in the database, wouldn't that be faster
    hash_values = map(hash_state_object, unmatched_states)
    equality_classes = collections.defaultdict(list)

    for (ndx, hashval) in enumerate(hash_values):
        equality_classes[hashval].append(ndx)

    canonical_states = [unmatched_states[equality_list[0]] for equality_list in
                        equality_classes.values()]
    canonical_state_ids = set([s.pk for s in canonical_states])
    noncanonical_states = [u for u in unmatched_states if u.pk not in canonical_state_ids]

    return canonical_states, noncanonical_states


def match_and_merge_unmatched_objects(unmatched_states, partitioner):
    """
    Take a list of unmatched_property_states or unmatched_tax_lot_states and returns a set of
    states that correspond to unmatched states.

    :param unmatched_states: list, PropertyStates or TaxLotStates
    :param partitioner: instance of EquivalencePartitioner
    :return: [list, list], merged_objects, equivalence_classes keys
    """
    # _log.debug("Starting to map_and_merge_unmatched_objects")

    # Sort unmatched states/This should not be happening!
    unmatched_states.sort(key=lambda state: state.pk)

    def getattrdef(obj, attr, default):
        if hasattr(obj, attr):
            return getattr(obj, attr)
        else:
            return default

    # create lambda function to sort the properties/taxlots by release_data first, then generation_date, and finally
    # the primary key
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
            merged_result = save_state_match(merged_result, unmatched)

        # 5/22/18 - I think this needs to be always run, not only if there wasn't more than one unmatched.
        # else:
        merged_objects.append(merged_result)

    # _log.debug("DONE with map_and_merge_unmatched_objects")
    return merged_objects, equivalence_classes.keys()


def merge_unmatched_into_views(unmatched_states, partitioner, org, import_file):
    """
    This is fairly inefficient, because we grab all the organization's entire PropertyViews at once.  Surely this can
    be improved, but the logic is unusual/particularly dynamic here, so hopefully this can be refactored into a better,
    purely database approach... Perhaps existing_view_states can wrap database calls. Still the abstractions are
    subtly different (can I refactor the partitioner to use Query objects); it may require a bit of thinking.

    :param unmatched_states:
    :param partitioner:
    :param org:
    :param import_file:
    :return:
    """

    # Cycle coming from the import_file does not make sense here. Makes testing hard. Should be an argument.
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
                        # Merge the new state in with the existing one and update the view,
                        # audit log.
                        current_view = existing_view_states[key][current_match_cycle]
                        current_state = current_view.state

                        merged_state = save_state_match(current_state, unmatched)

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


@shared_task(ignore_result=True)
@lock_and_track
def _match_properties_and_taxlots(file_pk, progress_key):
    """
    Match the properties and taxlots

    :param file_pk: ImportFile Primary Key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)
    progress_data = ProgressData.from_key(progress_key)

    # Don't query the org table here, just get the organization from the import_record
    org = import_file.import_record.super_organization

    # Set the progress to started
    progress_data.step()

    # Return a list of all the properties/tax lots based on the import file.
    all_unmatched_properties = import_file.find_unmatched_property_states()
    unmatched_properties = []
    unmatched_tax_lots = []
    duplicates_of_existing_property_states = []
    duplicates_of_existing_taxlot_states = []
    if all_unmatched_properties:
        # Filter out the duplicates within the import file.
        _log.debug("Start filter_duplicated_states: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        unmatched_properties, duplicate_property_states = filter_duplicated_states(
            all_unmatched_properties)
        _log.debug("End filter_duplicated_states: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        _log.debug("Start make_default_state_equivalence: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        property_partitioner = EquivalencePartitioner.make_default_state_equivalence(PropertyState)
        _log.debug("End make_default_state_equivalence: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner, while ignoring duplicates.
        _log.debug("Start match_and_merge_unmatched_objects: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        unmatched_properties, property_equivalence_keys = match_and_merge_unmatched_objects(
            unmatched_properties,
            property_partitioner
        )
        _log.debug("End match_and_merge_unmatched_objects: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        # TODO #239: This is quite slow... fix this next
        _log.debug("Start merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        merged_property_views = merge_unmatched_into_views(
            unmatched_properties,
            property_partitioner,
            org,
            import_file
        )
        _log.debug(
            "End merge_unmatched_into_views: %s" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Filter out the exact duplicates found in the previous step
        duplicates_of_existing_property_states = [state for state in unmatched_properties if
                                                  state.data_state == DATA_STATE_DELETE]
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
            taxlot_partitioner
        )

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        _log.debug("Start merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        merged_taxlot_views = merge_unmatched_into_views(
            unmatched_tax_lots,
            taxlot_partitioner,
            org,
            import_file
        )
        _log.debug("End merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Filter out the exact duplicates found in the previous step
        duplicates_of_existing_taxlot_states = [state for state in unmatched_tax_lots
                                                if state.data_state == DATA_STATE_DELETE]
        unmatched_tax_lots = [state for state in unmatched_tax_lots if
                              state not in duplicates_of_existing_taxlot_states]
    else:
        duplicate_tax_lot_states = []
        merged_taxlot_views = []

    # TODO #239: This is the next slowest... fix me too.
    _log.debug("Start pair_new_states: %s" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    progress_data.step()
    pair_new_states(merged_property_views, merged_taxlot_views)
    _log.debug("End pair_new_states: %s" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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

    return data


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
    ).select_related('state').order_by('state__id')

    ids = [p.state.id for p in pvs]
    return PropertyState.objects.filter(pk__in=ids)


def query_property_matches(properties, pm_id, custom_id, ubid):
    """
    Returns query set of PropertyStates that match at least one of the specified ids

    :param properties: QuerySet, PropertyStates
    :param pm_id: string, PM Property ID
    :param custom_id: String, Custom ID
    :param ubid: String, Unique Building Identifier
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
        params.append(Q(ubid=pm_id))
    if custom_id:
        params.append(Q(pm_property_id=custom_id))
        params.append(Q(custom_id_1=custom_id))
        params.append(Q(ubid=custom_id))
    if ubid:
        params.append(Q(pm_property_id=ubid))
        params.append(Q(custom_id_1=ubid))
        params.append(Q(ubid=ubid))

    if not params:
        # Return an empty QuerySet if we don't have any params.
        return properties.none()

    return properties.filter(reduce(operator.or_, params)).order_by('id')


def save_state_match(state1, state2):
    """
    Merge the contents of state2 into state1

    :param state1: PropertyState or TaxLotState
    :param state2: PropertyState or TaxLotState
    :return: state1, after merge
    """
    merged_state = type(state1).objects.create(organization=state1.organization)

    merged_state = merging.merge_state(merged_state,
                                       state1,
                                       state2,
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

    # If the two states being merged were just imported from the same import file, carry the import_file_id into the new
    # state. Also merge the lot_number fields so that pairing can work correctly on the resulting merged record
    # Possible conditions:
    # state1.data_state = 2, state1.merge_state = 0 and state2.data_state = 2, state2.merge_state = 0
    # state1.data_state = 0, state1.merge_state = 2 and state2.data_state = 2, state2.merge_state = 0
    if state1.import_file_id == state2.import_file_id:
        if ((
            state1.data_state == DATA_STATE_MAPPING and state1.merge_state == MERGE_STATE_UNKNOWN and
            state2.data_state == DATA_STATE_MAPPING and state2.merge_state == MERGE_STATE_UNKNOWN) or
            (
                state1.data_state == DATA_STATE_UNKNOWN and state1.merge_state == MERGE_STATE_MERGED and
                state2.data_state == DATA_STATE_MAPPING and state2.merge_state == MERGE_STATE_UNKNOWN)):
            merged_state.import_file_id = state1.import_file_id

            if isinstance(merged_state, PropertyState):
                joined_lots = set()
                if state1.lot_number:
                    joined_lots = joined_lots.union(state1.lot_number.split(';'))
                if state2.lot_number:
                    joined_lots = joined_lots.union(state2.lot_number.split(';'))
                if joined_lots:
                    merged_state.lot_number = ';'.join(joined_lots)

    # Set the merged_state to merged
    merged_state.merge_state = MERGE_STATE_MERGED
    merged_state.save()

    return merged_state


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

    tax_cmp_fmt = [
        ('jurisdiction_tax_lot_id', 'custom_id_1'),
        ('custom_id_1',),
        ('normalized_address',),
        ('custom_id_1',),
    ]

    prop_cmp_fmt = [
        ('lot_number', 'custom_id_1'),
        ('ubid',),
        ('custom_id_1',),
        ('normalized_address',),
        ('pm_property_id',),
        ('jurisdiction_property_id',),
    ]

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
