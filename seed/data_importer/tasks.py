# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.
:author
"""

from __future__ import absolute_import

import collections
import copy
import hashlib
import json
import os
import tempfile
import traceback
import zipfile
from bisect import bisect_left
from builtins import str
from collections import namedtuple
from datetime import date, datetime
from itertools import chain
from math import ceil

from _csv import Error
from celery import chain as celery_chain
from celery import chord, group, shared_task
from celery.utils.log import get_task_logger
from dateutil import parser
from django.contrib.gis.geos import GEOSGeometry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DataError, IntegrityError, connection, transaction
from django.db.utils import ProgrammingError
from django.utils import timezone as tz
from django.utils.timezone import make_naive
from past.builtins import basestring
from unidecode import unidecode

from seed.building_sync import validation_client
from seed.building_sync.building_sync import BuildingSync
from seed.data_importer.equivalence_partitioner import EquivalencePartitioner
from seed.data_importer.match import (
    match_and_link_incoming_properties_and_taxlots
)
from seed.data_importer.meters_parser import MetersParser
from seed.data_importer.models import (
    STATUS_READY_TO_MERGE,
    ImportFile,
    ImportRecord
)
from seed.data_importer.sensor_readings_parser import SensorsReadingsParser
from seed.data_importer.utils import usage_point_id
from seed.lib.mcm import cleaners, mapper, reader
from seed.lib.mcm.mapper import expand_rows
from seed.lib.mcm.utils import batch
from seed.lib.progress_data.progress_data import ProgressData
from seed.lib.superperms.orgs.models import Organization
from seed.lib.xml_mapping import reader as xml_reader
from seed.models import (
    ASSESSED_BS,
    ASSESSED_RAW,
    BUILDINGSYNC_RAW,
    DATA_STATE_DELETE,
    DATA_STATE_IMPORT,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    DATA_STATE_UNKNOWN,
    PORTFOLIO_BS,
    PORTFOLIO_RAW,
    BuildingFile,
    Column,
    ColumnMapping,
    DataLogger,
    Meter,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    Sensor,
    TaxLotAuditLog,
    TaxLotProperty,
    TaxLotState,
    TaxLotView
)
from seed.models.auditlog import AUDIT_IMPORT
from seed.models.data_quality import DataQualityCheck, Rule
from seed.utils.buildings import get_source_type
from seed.utils.geocode import MapQuestAPIKeyError, geocode_buildings
from seed.utils.match import update_sub_progress_total
from seed.utils.ubid import decode_unique_ids

# from seed.utils.cprofile import cprofile

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
    organization = qs.first().organization
    super_organization = organization.get_parent()
    d = DataQualityCheck.retrieve(super_organization.id)
    d.check_data(model, qs.iterator())
    d.save_to_cache(dq_id, organization.id)


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
    cache_key, dq_id = DataQualityCheck.initialize_cache(import_file_id, org_id)

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
        progress_data.finish_with_success()

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

    import_record.finish_time = tz.now()
    import_record.status = STATUS_READY_TO_MERGE
    import_record.save()

    return progress_data.finish_with_success()


def _build_cleaner(org):
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

    def _translate_unit_to_type(unit):
        if unit is None or unit == 'String':
            return 'string'

        return unit.lower()

    # start with the predefined types
    ontology = {'types': Column.retrieve_db_types()['types']}

    query_set = Column.objects.filter(organization=org, units_pint__isnull=False)
    for column in query_set:
        # DON'T OVERRIDE DEFAULT COLUMNS WITH DATA FROM RAW COLUMNS
        # THIS CAN HAPPEN IF YOU UPLOAD A FILE WITH A HEADER IDENTICAL TO THE DEFAULT COLUMN_NAME THAT ALSO HAS UNITS
        # LIKE 'site_eui' OR 'source_eui'
        # if column.column_name not in ontology['types']:
        # add available pint types as a tuple type
        ontology['types'][column.column_name] = ('quantity', column.units_pint)

    # find all the extra data columns with units and add them as well
    for column in Column.objects.filter(organization=org,
                                        is_extra_data=True).select_related('unit'):
        if column.unit:
            column_type = _translate_unit_to_type(column.unit.get_unit_type_display())
            ontology['types'][column.column_name] = column_type

    return cleaners.Cleaner(ontology)


@shared_task(ignore_result=True)
def map_row_chunk(ids, file_pk, source_type, prog_key, **kwargs):
    """Does the work of matching a mapping to a source type and saving

    :param ids: list of PropertyState IDs to map.
    :param file_pk: int, the PK for an ImportFile obj.
    :param source_type: int, represented by either ASSESSED_RAW or PORTFOLIO_RAW.
    :param prog_key: string, key of the progress key
    """
    progress_data = ProgressData.from_key(prog_key)
    import_file = ImportFile.objects.get(pk=file_pk)
    save_type = PORTFOLIO_BS
    if source_type == ASSESSED_RAW:
        save_type = ASSESSED_BS
    elif source_type == BUILDINGSYNC_RAW:
        save_type = BUILDINGSYNC_RAW

    org = Organization.objects.get(pk=import_file.import_record.super_organization.pk)

    # get all the table_mappings that exist for the organization
    table_mappings = ColumnMapping.get_column_mappings_by_table_name(org)

    # Remove any of the mappings that are not in the current list of raw columns because this
    # can really mess up the mapping of delimited_fields.
    # Ideally the table_mapping method would be attached to the import_file_id, someday...
    list_of_raw_columns = import_file.first_row_columns
    if list_of_raw_columns:
        for table, mappings in table_mappings.copy().items():
            for raw_column_name in mappings.copy():
                if raw_column_name not in list_of_raw_columns:
                    del table_mappings[table][raw_column_name]

        # check that the dictionaries are not empty, if empty, then delete.
        for table in table_mappings.copy():
            if not table_mappings[table]:
                del table_mappings[table]

    map_cleaner = _build_cleaner(org)

    # *** BREAK OUT INTO SEPARATE METHOD ***
    # figure out which import field is defined as the unique field that may have a delimiter of
    # individual values (e.g., tax lot ids). The definition of the delimited field is currently
    # hard coded
    try:
        delimited_fields = {}
        if 'TaxLotState' in table_mappings:
            tmp = list(table_mappings['TaxLotState'].keys())[
                list(table_mappings['TaxLotState'].values()).index(ColumnMapping.DELIMITED_FIELD)
            ]
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
    if 'PropertyState' in table_mappings:
        if delimited_fields and delimited_fields['jurisdiction_tax_lot_id']:
            table_mappings['PropertyState'][
                delimited_fields['jurisdiction_tax_lot_id']['from_field']] = (
                'PropertyState', 'lot_number', 'Lot Number', False)
    # *** END BREAK OUT ***
    try:
        with transaction.atomic():
            # yes, there are three cascading for loops here. sorry :(
            for table, mappings in table_mappings.items():
                if not table:
                    continue

                # This may be historic, but we need to pull out the extra_data_fields here to pass
                # into mapper.map_row. apply_columns are extra_data columns (the raw column names)
                extra_data_fields = []
                footprint_details = {}
                for k, v in mappings.items():
                    # the 3rd element is the is_extra_data flag.
                    # Need to convert this to a dict and not a tuple.
                    if v[3]:
                        extra_data_fields.append(k)

                    if v[1] in ['taxlot_footprint', 'property_footprint']:
                        footprint_details['raw_field'] = k
                        footprint_details['obj_field'] = v[1]

                # All the data live in the PropertyState.extra_data field when the data are imported
                data = PropertyState.objects.filter(id__in=ids).only('extra_data',
                                                                     'bounding_box').iterator()

                # Since we are importing CSV, then each extra_data field will have the same fields.
                # So save the map_model_obj outside of for loop to pass into the `save_column_names`
                # methods
                map_model_obj = None

                # Loop over all the rows
                for original_row in data:
                    # expand the row into multiple rows if needed with the delimited_field replaced
                    # with a single value. This minimizes the need to rewrite the downstream code.
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
                    for row in expand_rows(
                        original_row.extra_data, delimited_field_list, expand_row
                    ):
                        map_model_obj = mapper.map_row(
                            row,
                            mappings,
                            STR_TO_CLASS[table],
                            extra_data_fields,
                            cleaner=map_cleaner,
                            **kwargs
                        )

                        # save cross related data, that is data that needs to go into the other
                        # model's collection as well.

                        # Assign some other arguments here
                        map_model_obj.bounding_box = original_row.bounding_box
                        map_model_obj.import_file = import_file
                        map_model_obj.source_type = save_type
                        map_model_obj.organization = import_file.import_record.super_organization
                        if hasattr(map_model_obj, 'data_state'):
                            map_model_obj.data_state = DATA_STATE_MAPPING
                        if hasattr(map_model_obj, 'clean'):
                            map_model_obj.clean()

                        # There is a potential thread safe issue here:
                        # This method is called in parallel on production systems, so we need to
                        # make sure that the object hasn't already been created. For example, in
                        # the test data the tax lot id is the same for many rows. Make sure
                        # to only create/save the object if it hasn't been created before.
                        if hash_state_object(map_model_obj, include_extra_data=False) == \
                            hash_state_object(
                                STR_TO_CLASS[table](organization=map_model_obj.organization),
                                include_extra_data=False):
                            # Skip this object as it has no data...
                            _log.warning(
                                "Skipping property or taxlot during mapping because it is identical to another row")
                            continue

                        # If a footprint was provided but footprint was not populated/valid,
                        # create a new extra_data column to store the raw, invalid data.
                        # Also create a new rule for this new column
                        if footprint_details.get('obj_field'):
                            if getattr(map_model_obj, footprint_details['obj_field']) is None:
                                _store_raw_footprint_and_create_rule(footprint_details, table, org, import_file,
                                                                     original_row, map_model_obj)

                        # There was an error with a field being too long [> 255 chars].
                        map_model_obj.save()

                        # if importing BuildingSync create a BuildingFile for the property
                        if source_type == BUILDINGSYNC_RAW:
                            raw_ps_id = original_row.id
                            xml_filename = import_file.raw_property_state_to_filename.get(str(raw_ps_id))
                            if xml_filename is None:
                                raise Exception('Expected ImportFile to have the raw PropertyStates id in its raw_property_state_to_filename dict')

                            from_zipfile = import_file.uploaded_filename.endswith('.zip')
                            # if user uploaded a zipfile, find the xml file related to this property and use it
                            # else, the user uploaded a sole xml file and we can just use that one.
                            if from_zipfile:
                                with zipfile.ZipFile(import_file.file, 'r', zipfile.ZIP_STORED) as openzip:
                                    new_file = SimpleUploadedFile(
                                        name=xml_filename,
                                        content=openzip.read(xml_filename),
                                        content_type='application/xml')
                            else:
                                xml_filename = import_file.uploaded_filename
                                if xml_filename == '':
                                    raise Exception('Expected ImportFiles uploaded_filename to be non-empty')
                                new_file = SimpleUploadedFile(
                                    name=xml_filename,
                                    content=import_file.file.read(),
                                    content_type='application/xml'
                                )

                            building_file = BuildingFile.objects.create(
                                file=new_file,
                                filename=xml_filename,
                                file_type=BuildingFile.BUILDINGSYNC,
                            )

                            # link the property state to the building file
                            building_file.property_state = map_model_obj
                            building_file.save()

                        # Create an audit log record for the new map_model_obj that was created.

                        AuditLogClass = PropertyAuditLog if isinstance(
                            map_model_obj, PropertyState) else TaxLotAuditLog
                        AuditLogClass.objects.create(
                            organization=org,
                            state=map_model_obj,
                            name='Import Creation',
                            description='Creation from Import file.',
                            import_filename=import_file,
                            record_type=AUDIT_IMPORT
                        )

                # Make sure that we've saved all of the extra_data column names from the first item
                # in list
                if map_model_obj:
                    Column.save_column_names(map_model_obj)
    except IntegrityError as e:
        progress_data.finish_with_error('Could not map_row_chunk with error', str(e))
        raise IntegrityError("Could not map_row_chunk with error: %s" % str(e))
    except DataError as e:
        _log.error(traceback.format_exc())
        progress_data.finish_with_error('Invalid data found', str(e))
        raise DataError("Invalid data found: %s" % str(e))
    except TypeError as e:
        _log.error('Error mapping data with error: %s' % str(e))
        progress_data.finish_with_error('Invalid type found while mapping data', str(e))
        raise DataError("Invalid type found while mapping data: %s" % str(e))

    progress_data.step()

    return True


def _store_raw_footprint_and_create_rule(footprint_details, table, org, import_file, original_row, map_model_obj):
    column_name = footprint_details['raw_field'] + ' (Invalid Footprint)'

    column_mapping_for_cache = {
        'from_field': column_name,
        'from_units': None,
        'to_field': column_name,
        'to_table_name': table
    }

    column_mapping = column_mapping_for_cache.copy()
    column_mapping['to_field_display_name'] = column_name

    # Create column without updating the mapped columns cache, then update cache separately
    Column.create_mappings([column_mapping], org, import_file.import_record.last_modified_by)

    cached_column_mapping = json.loads(import_file.cached_mapped_columns)
    cached_column_mapping.append(column_mapping_for_cache)
    import_file.save_cached_mapped_columns(cached_column_mapping)

    map_model_obj.extra_data[column_name] = original_row.extra_data[footprint_details['raw_field']]

    rule = {
        'table_name': table,
        'field': column_name,
        'rule_type': Rule.RULE_TYPE_CUSTOM,
        'severity': Rule.SEVERITY_ERROR,
    }

    dq, _created = DataQualityCheck.objects.get_or_create(organization=org.id)
    dq.add_rule_if_new(rule)


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
    # if not import_file.raw_save_done:
    #     _log.debug("_map_data raw_save_done is false, queueing the task until raw_save finishes")
    #     map_data.apply_async(args=[import_file_id], countdown=60, expires=120)
    #     return progress_data.finish_with_error('waiting for raw data save.')

    source_type_dict = {
        'Portfolio Raw': PORTFOLIO_RAW,
        'Assessed Raw': ASSESSED_RAW,
        'BuildingSync Raw': BUILDINGSYNC_RAW
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

    :param org_id:
    :param property_state_ids: list, list of property state IDs to check
    :param taxlot_state_ids: list, list of tax lot state IDs to check
    :param dq_id: str, for retrieving progress status
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


def map_data(import_file_id, remap=False, mark_as_done=True):
    """
    Map data task. By default this method will run through the mapping and mark it as complete.
    :param import_file_id: Import File ID
    :param remap: bool, if remapping, then delete previous objects from the database
    :param mark_as_done: bool, if skip review then the mapping_done flag will be set to true at the
    end.
    :return: JSON
    """
    import_file = ImportFile.objects.get(pk=import_file_id)

    # Clear out the previously mapped data
    DataQualityCheck.initialize_cache(import_file_id, import_file.import_record.super_organization.id)

    # Check for duplicate column headers
    column_headers = import_file.first_row_columns or []
    duplicate_tracker = collections.defaultdict(lambda: 0)
    for header in column_headers:
        duplicate_tracker[header] += 1
        if duplicate_tracker[header] > 1:
            raise Exception("Duplicate column found in file: %s" % (header))

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
    :param progress_key: string, Progress Key to append progress
    :return: Bool, Always true
    """
    import_file = ImportFile.objects.get(pk=file_pk)

    # Save our "column headers" and sample rows for F/E.
    source_type = get_source_type(import_file)

    # BuildingSync only: track property state ID to its source filename
    raw_property_state_to_filename = {}
    try:
        with transaction.atomic():
            for c in chunk:
                raw_property = PropertyState(
                    organization=import_file.import_record.super_organization)
                raw_property.import_file = import_file

                # sanitize c and remove any diacritics
                new_chunk = {}
                for k, v in c.items():
                    # remove extra spaces surrounding keys.
                    key = k.strip()

                    source_filename = None
                    if key == "bounding_box":  # capture bounding_box GIS field on raw record
                        raw_property.bounding_box = v
                    elif key == "_source_filename":  # grab source filename (for BSync)
                        source_filename = v
                    elif isinstance(v, basestring):
                        new_chunk[key] = unidecode(v)
                    elif isinstance(v, (datetime, date)):
                        raise TypeError(
                            "Datetime class not supported in Extra Data. Needs to be a string.")
                    else:
                        new_chunk[key] = v
                raw_property.extra_data = new_chunk
                raw_property.source_type = source_type
                raw_property.data_state = DATA_STATE_IMPORT
                raw_property.organization = import_file.import_record.super_organization
                raw_property.save()

                if source_filename is not None:
                    raw_property_state_to_filename[str(raw_property.id)] = source_filename

    except IntegrityError as e:
        raise IntegrityError("Could not save_raw_data_chunk with error: %s" % (e))

    # Indicate progress
    progress_data = ProgressData.from_key(progress_key)
    progress_data.step()

    return raw_property_state_to_filename


@shared_task(ignore_result=True)
def finish_raw_save(results, file_pk, progress_key):
    """
    Finish importing the raw file.

    If the file is a PM Meter Usage or GreenButton import, remove the cycle association.
    If the file is of one of those types and a summary is provided, add import results
    to this summary and save it to the ProgressData.

    :param results: List of results from the parent task
    :param file_pk: ID of the file that was being imported
    :param progress_key: string, Progress Key to append progress
    :param summary: Summary to be saved on ProgressData as a message
    :return: results: results from the other tasks before the chord ran
    """
    progress_data = ProgressData.from_key(progress_key)
    import_file = ImportFile.objects.get(pk=file_pk)
    import_file.raw_save_done = True

    if import_file.source_type in ['PM Meter Usage', 'GreenButton'] and progress_data.summary() is not None:
        import_file.cycle_id = None

        new_summary = _append_meter_import_results_to_summary(results, progress_data.summary())
        finished_progress_data = progress_data.finish_with_success(new_summary)
    elif import_file.source_type == "SensorMetaData":
        import_file.cycle_id = None
        new_summary = _append_sensor_import_results_to_summary(results)
        finished_progress_data = progress_data.finish_with_success(new_summary)

    elif import_file.source_type == "SensorReadings":
        new_summary = _append_sensor_readings_import_results_to_summary(results)
        finished_progress_data = progress_data.finish_with_success(new_summary)

    else:
        finished_progress_data = progress_data.finish_with_success()

    if import_file.source_type == 'BuildingSync Raw':
        for result in results:
            import_file.raw_property_state_to_filename.update(result)

    import_file.save()

    return finished_progress_data


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


@shared_task
def _save_greenbutton_data_create_tasks(file_pk, progress_key):
    """
    Create GreenButton import tasks. Notably, 1 GreenButton import contains
    data for 1 Property and 1 energy type. Subsequently, this means 1
    GreenButton import contains MeterReadings for only 1 Meter.

    By first getting or creating the single Meter for this file's MeterReadings,
    the ID of this Meter can be passed to the individual tasks that will
    actually create the readings.
    """
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=file_pk)
    org_id = import_file.cycle.organization.id
    property_id = import_file.matching_results_data['property_id']

    # matching_results_data gets cleared out since the field wasn't meant for this
    import_file.matching_results_data = {}
    import_file.save()

    parser = reader.GreenButtonParser(import_file.local_file)
    raw_meter_data = list(parser.data)

    meters_parser = MetersParser(org_id, raw_meter_data, source_type=Meter.GREENBUTTON, property_id=property_id)
    meter_readings = meters_parser.meter_and_reading_objs[0]  # there should only be one meter (1 property, 1 type/unit)

    readings = meter_readings['readings']
    meter_only_details = {k: v for k, v in meter_readings.items() if k != 'readings'}
    meter, _created = Meter.objects.get_or_create(**meter_only_details)
    meter_id = meter.id

    meter_usage_point_id = usage_point_id(meter.source_id)

    chunk_size = 1000

    # add in the proposed_imports into the progress key to be used later. (This used to be the summary).
    progress_data.update_summary(meters_parser.proposed_imports)
    progress_data.total = ceil(len(readings) / chunk_size)
    progress_data.save()

    tasks = []
    # Add in the save raw data chunks to the background tasks
    for batch_readings in batch(readings, chunk_size):
        tasks.append(_save_greenbutton_data_task.s(batch_readings, meter_id, meter_usage_point_id, progress_data.key))

    return chord(tasks, interval=15)(finish_raw_save.s(file_pk, progress_data.key))


@shared_task
def _save_sensor_data_create_tasks(file_pk, progress_key):
    """
    Create or Edit Sensor tasks. Creates multiple sensors for the same property.
    """
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=file_pk)
    data_logger_id = import_file.matching_results_data['data_logger_id']
    data_logger = DataLogger.objects.get(id=data_logger_id)

    # matching_results_data gets cleared out since the field wasn't meant for this
    import_file.matching_results_data = {}
    import_file.save()

    parser = reader.MCMParser(import_file.local_file)
    sensor_data = list(parser.data)

    sensors = []
    for sensor_datum in sensor_data:
        s, _ = Sensor.objects.get_or_create(**{
            "column_name": sensor_datum["column_name"],
            "data_logger": data_logger
        })
        s.display_name = sensor_datum["display_name"]
        s.location_description = sensor_datum["location_description"]
        s.description = sensor_datum["description"]
        s.sensor_type = sensor_datum["type"]
        s.units = sensor_datum["units"]

        s.save()
        sensors.append(s)

    # add in the proposed_imports into the progress key to be used later. (This used to be the summary).
    progress_data.total = 0
    progress_data.save()

    return finish_raw_save(sensors, file_pk, progress_data.key)


@shared_task
def _save_sensor_readings_data_create_tasks(file_pk, progress_key):
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=file_pk)
    org_id = import_file.cycle.organization.id
    data_logger_id = import_file.matching_results_data['data_logger_id']

    # matching_results_data gets cleared out since the field wasn't meant for this
    import_file.matching_results_data = {}
    import_file.save()

    parser = SensorsReadingsParser.factory(
        import_file.local_file,
        org_id,
        data_logger_id=data_logger_id
    )
    sensor_readings_data = parser.sensor_readings_details

    tasks = []
    chunk_size = 500
    for sensor_column_name, readings in sensor_readings_data.items():
        readings_tuples = [t for t in readings.items()]
        for batch_readings in batch(readings_tuples, chunk_size):
            tasks.append(_save_sensor_readings_task.s(batch_readings, data_logger_id, sensor_column_name, progress_data.key))

    progress_data.total = len(tasks)
    progress_data.save()

    return chord(tasks, interval=15)(finish_raw_save.s(file_pk, progress_data.key))


@shared_task
def _save_sensor_readings_task(readings_tuples, data_logger_id, sensor_column_name, progress_key):
    progress_data = ProgressData.from_key(progress_key)

    result = {}
    try:
        sensor = Sensor.objects.get(data_logger_id=data_logger_id, column_name=sensor_column_name)

    except Sensor.DoesNotExist:
        result[sensor_column_name] = {'error': 'No such sensor.'}

    else:
        try:
            with transaction.atomic():
                is_occupied_data = DataLogger.objects.get(id=data_logger_id).is_occupied_data
                [occupied_timestamps, is_occupied_arr] = list(zip(*is_occupied_data))
                occupied_timestamps = [datetime.fromisoformat(t) for t in occupied_timestamps]

                reading_strings = []
                for timestamp, value in readings_tuples:
                    is_occupied = is_occupied_arr[bisect_left(occupied_timestamps, parser.parse(timestamp)) - 1]
                    reading_strings.append(f"({sensor.id}, '{timestamp}', '{value}', '{is_occupied}')")

                sql = (
                    'INSERT INTO seed_sensorreading(sensor_id, timestamp, reading, is_occupied)' +
                    ' VALUES ' + ', '.join(reading_strings) +
                    ' ON CONFLICT (sensor_id, timestamp)' +
                    ' DO UPDATE SET reading = EXCLUDED.reading' +
                    ' RETURNING reading;'
                )
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    result[sensor_column_name] = {'count': len(cursor.fetchall())}
        except ProgrammingError as e:
            if 'ON CONFLICT DO UPDATE command cannot affect row a second time' in str(e):
                result[sensor_column_name] = {'error': 'Overlapping readings.'}
            else:
                progress_data.finish_with_error('data failed to import')
                raise e
        except DataError as e:
            if "date/time field" in str(e):
                result[sensor_column_name] = {'error': 'Invalid readings. Ensure timestamps are in iso format.'}
            elif "invalid input syntax for type double precision" in str(e):
                result[sensor_column_name] = {'error': 'Invalid readings. Ensure readings are numbers.'}
            else:
                result[sensor_column_name] = {'error': 'Invalid readings.'}

        except Exception as e:
            progress_data.finish_with_error('data failed to import')
            raise e

    progress_data.step()

    return result


@shared_task
def _save_greenbutton_data_task(readings, meter_id, meter_usage_point_id, progress_key):
    """
    This method defines an individual task to save MeterReadings for a single
    Meter. Each task returns the results of the import.

    The query creates or updates readings while associating them to the meter
    via raw SQL upsert. Specifically, meter_id, start_time, and end_time must be
    unique or an update occurs. Otherwise, a new reading entry is created.

    If the query leads to an error regarding trying to update the same row
    within the same query, the error is logged in the results and none of the
    readings for that batch are saved.
    """
    progress_data = ProgressData.from_key(progress_key)
    meter = Meter.objects.get(pk=meter_id)

    result = {}
    result_summary_key = "{} - {} - {}".format(
        meter.property_id,
        meter_usage_point_id,
        meter.get_type_display()
    )

    try:
        with transaction.atomic():
            reading_strings = [
                f"({meter_id}, '{reading['start_time'].isoformat(' ')}', '{reading['end_time'].isoformat(' ')}', {reading['reading']}, '{reading['source_unit']}', {reading['conversion_factor']})"
                for reading
                in readings
            ]

            sql = (
                'INSERT INTO seed_meterreading(meter_id, start_time, end_time, reading, source_unit, conversion_factor)' +
                ' VALUES ' + ', '.join(reading_strings) +
                ' ON CONFLICT (meter_id, start_time, end_time)' +
                ' DO UPDATE SET reading = EXCLUDED.reading, source_unit = EXCLUDED.source_unit, conversion_factor = EXCLUDED.conversion_factor' +
                ' RETURNING reading;'
            )
            with connection.cursor() as cursor:
                cursor.execute(sql)
                result[result_summary_key] = {'count': len(cursor.fetchall())}
    except ProgrammingError as e:
        if 'ON CONFLICT DO UPDATE command cannot affect row a second time' in str(e):
            result[result_summary_key] = {'error': 'Overlapping readings.'}
        else:
            progress_data.finish_with_error('data failed to import')
            raise e
    except Exception as e:
        progress_data.finish_with_error('data failed to import')
        raise e

    # Indicate progress
    progress_data.step()

    return result


@shared_task
def _save_pm_meter_usage_data_task(meter_readings, file_pk, progress_key):
    """
    This method defines an individual task to get or create a single Meter and its
    corresponding MeterReadings. Each task returns the results of the import.

    Within the query, get or create the meter without it's readings. Then,
    create or update readings while associating them to the meter via raw SQL upsert.
    Specifically, meter_id, start_time, and end_time must be unique or an update
    occurs. Otherwise, a new reading entry is created.

    If the query leads to an error regarding trying to update the same row
    within the same query, the error is logged in the results and all the
    MeterReadings and their Meter (if that was created in this transaction) are
    not saved.
    """
    progress_data = ProgressData.from_key(progress_key)

    result = {}
    try:
        with transaction.atomic():
            readings = meter_readings['readings']
            meter_only_details = {k: v for k, v in meter_readings.items() if k != 'readings'}

            meter, _created = Meter.objects.get_or_create(**meter_only_details)

            reading_strings = [
                f"({meter.id}, '{reading['start_time'].isoformat(' ')}', '{reading['end_time'].isoformat(' ')}', {reading['reading']}, '{reading['source_unit']}', {reading['conversion_factor']})"
                for reading
                in readings
            ]

            sql = (
                'INSERT INTO seed_meterreading(meter_id, start_time, end_time, reading, source_unit, conversion_factor)' +
                ' VALUES ' + ', '.join(reading_strings) +
                ' ON CONFLICT (meter_id, start_time, end_time)' +
                ' DO UPDATE SET reading = EXCLUDED.reading, source_unit = EXCLUDED.source_unit, conversion_factor = EXCLUDED.conversion_factor' +
                ' RETURNING reading;'
            )
            with connection.cursor() as cursor:
                cursor.execute(sql)
                key = "{} - {} - {}".format(
                    meter.property_id,
                    meter.source_id,
                    meter.get_type_display()
                )
                result[key] = {'count': len(cursor.fetchall())}
    except ProgrammingError as e:
        if 'ON CONFLICT DO UPDATE command cannot affect row a second time' in str(e):
            type_lookup = dict(Meter.ENERGY_TYPES)
            key = "{} - {} - {}".format(
                meter_readings.get('property_id'),
                meter_readings.get('source_id'),
                type_lookup[meter_readings['type']]
            )
            result[key] = {'error': 'Overlapping readings.'}
        else:
            progress_data.finish_with_error('data failed to import')
            raise e
    except Exception as e:
        progress_data.finish_with_error('data failed to import')
        raise e

    progress_data.step()

    return result


@shared_task
def _save_pm_meter_usage_data_create_tasks(file_pk, progress_key):
    """
    This takes a PM meters import file and restructures the data in order to
    create and return the tasks to import Meters and their corresponding
    MeterReadings.

    In addition, a snapshot of the proposed imports are passed back to later
    create a before and after summary of the import.

    :param file_pk: int, ID of the file to import
    :param progress_key: string, Progress Key to append progress
    """
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=file_pk)
    org_id = import_file.cycle.organization.id

    meters_parser = MetersParser.factory(import_file.local_file, org_id)
    meters_and_readings = meters_parser.meter_and_reading_objs

    # add in the proposed_imports into the progress key to be used later. (This used to be the summary).
    progress_data.update_summary(meters_parser.proposed_imports)
    progress_data.total = len(meters_and_readings)
    progress_data.save()

    tasks = []
    for meter_readings in meters_and_readings:
        tasks.append(_save_pm_meter_usage_data_task.s(meter_readings, file_pk, progress_data.key))

    return chord(tasks, interval=15)(finish_raw_save.s(file_pk, progress_data.key))


def _append_meter_import_results_to_summary(import_results, incoming_summary):
    """
    This appends meter import result counts and, if applicable, error messages.

    Note, import_results will be of the form:
        [
            {'<source_id/usage_point_id> - <type>": {'count': 100}},
            {'<source_id/usage_point_id> - <type>": {'count': 100}},
            {'<source_id/usage_point_id> - <type>": {'error': "<error_message>"}},
            {'<source_id/usage_point_id> - <type>": {'error': "<error_message>"}},
        ]
    """
    agg_results_summary = collections.defaultdict(lambda: 0)
    error_comments = collections.defaultdict(lambda: set())

    if not isinstance(import_results, list):
        import_results = [import_results]

    # First aggregate import_results by key
    for result in import_results:
        key = list(result.keys())[0]

        success_count = result[key].get('count')

        if success_count is None:
            error_comments[key].add(result[key].get('error'))
        else:
            agg_results_summary[key] += success_count

    # Next update summary of incoming meters imports with aggregated results.
    for import_info in incoming_summary:
        key = "{} - {} - {}".format(
            import_info['property_id'],
            import_info['source_id'],
            import_info['type']
        )

        # check if there has already been a successfully_imported count on this key
        successfully_imported = import_info.get('successfully_imported', 0)
        import_info['successfully_imported'] = agg_results_summary.get(key, successfully_imported)

        if error_comments:
            import_info['errors'] = ' '.join(list(error_comments.get(key, '')))

    return incoming_summary


def _append_sensor_import_results_to_summary(import_results):
    return [
        {
            "display_name": sensor.display_name,
            "type": sensor.sensor_type,
            "location_description": sensor.location_description,
            "units": sensor.units,
            "column_name": sensor.column_name,
            "description": sensor.description,
        }
        for sensor in import_results
    ]


def _append_sensor_readings_import_results_to_summary(import_results):
    summary = {}
    for import_result in import_results:
        sensor_name, result = list(import_result.items())[0]

        if sensor_name not in summary:
            summary[sensor_name] = {
                "column_name": sensor_name,
                "num_readings": 0,
                "errors": ""
            }

        if "count" in result:
            summary[sensor_name]["num_readings"] += result["count"]

        if "error" in result:
            summary[sensor_name]["errors"] = result["error"]

    return list(summary.values())


@shared_task
def _save_raw_data_create_tasks(file_pk, progress_key):
    """
    Worker method for saving raw data. Chunk up the CSV, XLSX, geojson/json file and create the tasks
    to save the raw data into the PropertyState table.

    :param file_pk: int, ID of the file to import
    :return: Dict, result from progress data / cache
    """
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=file_pk)
    file_extension = os.path.splitext(import_file.file.name)[1]

    if file_extension == '.json' or file_extension == '.geojson':
        parser = reader.GeoJSONParser(import_file.local_file)
    elif import_file.source_type == 'BuildingSync Raw':
        try:
            parser = xml_reader.BuildingSyncParser(import_file.file)
        except Exception as e:
            return progress_data.finish_with_error(f'Failed to parse BuildingSync data: {str(e)}')
    else:
        try:
            parser = reader.MCMParser(import_file.local_file)
        except Exception as e:
            _log.debug(f'Error reading XLSX file: {str(e)}')
            return progress_data.finish_with_error('Failed to parse XLSX file. Please review your import file - all headers should be present and non-numeric.')

    import_file.has_generated_headers = False
    if hasattr(parser, 'has_generated_headers'):
        import_file.has_generated_headers = parser.has_generated_headers

    cache_first_rows(import_file, parser)
    import_file.num_rows = 0
    import_file.num_columns = parser.num_columns()

    chunks = []
    for batch_chunk in batch(parser.data, 100):
        import_file.num_rows += len(batch_chunk)
        chunks.append(batch_chunk)
    import_file.save()

    progress_data.total = len(chunks)
    progress_data.save()

    # Add in the save raw data chunks to the background tasks
    tasks = []
    for chunk in chunks:
        tasks.append(_save_raw_data_chunk.s(chunk, file_pk, progress_data.key))

    return chord(tasks, interval=15)(finish_raw_save.s(file_pk, progress_data.key))


def save_raw_data(file_pk):
    """
    Simply report to the user that we have queued up the save_run_data to run. This is the entry
    point into saving the data.

    In the case of meter reading imports, it's possible to receive a summary of
    what the tasks intend to accomplish.

    :param file_pk: ImportFile Primary Key
    :return: Dict, from cache, containing the progress key to track
    """
    progress_data = ProgressData(func_name='save_raw_data', unique_id=file_pk)
    try:
        # Go get the tasks that need to be created, then call them in the chord here.
        import_file = ImportFile.objects.get(pk=file_pk)
        if import_file.raw_save_done:
            return progress_data.finish_with_warning('Raw data already saved')

        # queue up the tasks and immediately return. This is needed in the case of large files
        # and slow transfers causing the website to timeout due to inactivity. Specifically, the chunking method of
        # large files can take quite some time.
        if import_file.source_type == 'PM Meter Usage':
            _save_pm_meter_usage_data_create_tasks.s(file_pk, progress_data.key).delay()
        elif import_file.source_type == 'GreenButton':
            _save_greenbutton_data_create_tasks.s(file_pk, progress_data.key).delay()
        elif import_file.source_type == 'SensorMetaData':
            _save_sensor_data_create_tasks.s(file_pk, progress_data.key).delay()
        elif import_file.source_type == 'SensorReadings':
            _save_sensor_readings_data_create_tasks.s(file_pk, progress_data.key).delay()
        else:
            _save_raw_data_create_tasks.s(file_pk, progress_data.key).delay()
    except StopIteration:
        progress_data.finish_with_error('StopIteration Exception', traceback.format_exc())
    except Error as e:
        progress_data.finish_with_error('File Content Error: ' + str(e), traceback.format_exc())
    except KeyError as e:
        progress_data.finish_with_error('Invalid Column Name: "' + str(e) + '"', traceback.format_exc())
    except TypeError:
        progress_data.finish_with_error('TypeError Exception', traceback.format_exc())
    except Exception as e:
        progress_data.finish_with_error('Unhandled Error: ' + str(e), traceback.format_exc())
    return progress_data.result()


def geocode_and_match_buildings_task(file_pk):
    import_file = ImportFile.objects.get(pk=file_pk)

    progress_data = ProgressData(func_name='match_buildings', unique_id=file_pk)
    progress_data.delete()
    sub_progress_data = ProgressData(func_name='match_sub_progress', unique_id=file_pk)
    sub_progress_data.delete()

    if import_file.matching_done:
        _log.debug('Matching is already done')
        return progress_data.finish_with_warning('matching already complete')

    if not import_file.mapping_done:
        _log.debug('Mapping is not done yet')
        return progress_data.finish_with_error(
            'Import file is not complete. Retry after mapping is complete', )

    if import_file.cycle is None:
        _log.warning("Import file cycle is None; This should never happen in production")

    # get the properties and chunk them into tasks
    property_states = (
        PropertyState.objects.filter(import_file_id=file_pk)
        .exclude(data_state=DATA_STATE_IMPORT)
        .only('id')
        .iterator()
    )

    id_chunks = [[obj.id for obj in chunk] for chunk in batch(property_states, 100)]

    progress_data.total = (
        1  # geocoding
        + len(id_chunks)  # map additional models tasks
        + 2  # match and link
        + 1  # finish
    )
    progress_data.save()

    celery_chain(
        _geocode_properties_or_tax_lots.si(file_pk, progress_data.key),
        group(_map_additional_models.si(id_chunk, file_pk, progress_data.key) for id_chunk in id_chunks),
        match_and_link_incoming_properties_and_taxlots.si(file_pk, progress_data.key, sub_progress_data.key),
        finish_matching.s(file_pk, progress_data.key),
    )()

    sub_progress_data.total = 100
    sub_progress_data.save()

    return {'progress_data': progress_data.result(), 'sub_progress_data': sub_progress_data.result()}


def geocode_buildings_task(file_pk):
    """
    NOTE: This is an older entrypoint into geocoding buildings and should no longer
    be used. Use geocode_and_match_buildings_task instead.
    TODO: remove this task once api v2 is removed
    """
    progress_data = ProgressData(func_name='geocode_buildings', unique_id=file_pk)
    progress_data.delete()
    progress_data.save()
    async_result = _geocode_properties_or_tax_lots.s(file_pk, progress_data.key).apply_async()
    result = [r for r in async_result.collect()]

    return result


@shared_task
def _geocode_properties_or_tax_lots(file_pk, progress_key, sub_progress_key=None):
    progress_data = ProgressData.from_key(progress_key)
    sub_progress_data = update_sub_progress_total(3, sub_progress_key)

    progress_data.step('Geocoding')
    if sub_progress_key:
        sub_progress_data.step('Geocoding')

    property_state_qs = PropertyState.objects.filter(import_file_id=file_pk).exclude(data_state=DATA_STATE_IMPORT)
    if property_state_qs:
        decode_unique_ids(property_state_qs)
        try:
            geocode_buildings(property_state_qs)
        except MapQuestAPIKeyError as e:
            progress_data.finish_with_error(str(e), traceback.format_exc())
            raise e

    if sub_progress_key:
        sub_progress_data.step('Geocoding')

    tax_lot_state_qs = TaxLotState.objects.filter(import_file_id=file_pk).exclude(data_state=DATA_STATE_IMPORT)
    if tax_lot_state_qs:
        decode_unique_ids(tax_lot_state_qs)
        try:
            geocode_buildings(tax_lot_state_qs)
        except MapQuestAPIKeyError as e:
            progress_data.finish_with_error(str(e), traceback.format_exc())
            raise e

    if sub_progress_key:
        sub_progress_data.step('Geocoding')
        sub_progress_data.finish_with_success()


def map_additional_models(file_pk):
    """
    NOTE: This is an older entrypoint into mapping buildings and should no longer
    be used. Use geocode_and_match_buildings_task instead.
    TODO: remove this task once api v2 is removed

    kicks off mapping models other than PropertyState, returns progress key within the JSON response
    E.g. It creates the PropertyView, Property, Scenario, Meters, etc for BuildingSync files

    :param file_pk: ImportFile Primary Key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)

    progress_data = ProgressData(func_name='match_buildings', unique_id=file_pk)
    progress_data.delete()
    progress_data.save()

    if import_file.matching_done:
        _log.debug('Matching is already done')
        return progress_data.finish_with_warning('matching already complete')

    if not import_file.mapping_done:
        _log.debug('Mapping is not done yet')
        return progress_data.finish_with_error(
            'Import file is not complete. Retry after mapping is complete', )

    if import_file.cycle is None:
        _log.warning("This should never happen in production")

    source_type_dict = {
        'Portfolio Raw': PORTFOLIO_RAW,
        'Assessed Raw': ASSESSED_RAW,
        'BuildingSync Raw': BUILDINGSYNC_RAW
    }
    source_type = source_type_dict.get(import_file.source_type, ASSESSED_RAW)

    # get the properties and chunk them into tasks
    qs = PropertyState.objects.filter(
        import_file=import_file,
        source_type=source_type,
        data_state=DATA_STATE_MAPPING,
    ).only('id').iterator()

    id_chunks = [[obj.id for obj in chunk] for chunk in batch(qs, 100)]

    progress_data.total = len(id_chunks)
    progress_data.save()

    tasks = [_map_additional_models.si(ids, import_file.id, progress_data.key)
             for ids in id_chunks]

    chord(tasks)(
        finish_mapping_additional_models.s(file_pk, progress_data.key))

    return progress_data.result()


@shared_task(ignore_result=True)
def finish_mapping_additional_models(result, import_file_id, progress_key):
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=import_file_id)
    import_file.matching_done = True
    import_file.mapping_completion = 100
    if isinstance(result, list) and len(result) >= 0:
        # merge the results from the tasks
        # assumes that all values are numbers
        merged_result = {}
        for res in result:
            for key, value in res.items():
                if key in merged_result:
                    merged_result[key] += value
                else:
                    merged_result[key] = value

        import_file.matching_results_data = merged_result
    else:
        raise Exception('Expected result to be a list of one or more items')

    import_file.save()
    return progress_data.finish_with_success()


# @cprofile()
def match_buildings(file_pk):
    """
    NOTE: This is an older entrypoint into matching buildings and should no longer
    be used. Use geocode_and_match_buildings_task instead.
    TODO: remove this task once api v2 is removed

    kicks off system matching, returns progress key within the JSON response

    :param file_pk: ImportFile Primary Key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)

    progress_data = ProgressData(func_name='match_buildings', unique_id=file_pk)
    progress_data.delete()
    sub_progress_data = ProgressData(func_name='match_sub_progress', unique_id=file_pk)
    sub_progress_data.delete()

    if import_file.matching_done:
        _log.debug('Matching is already done')
        return progress_data.finish_with_warning('matching already complete')

    if not import_file.mapping_done:
        _log.debug('Mapping is not done yet')
        return progress_data.finish_with_error(
            'Import file is not complete. Retry after mapping is complete', )

    if import_file.cycle is None:
        _log.warning('This should never happen in production')

    # Start, match, pair
    progress_data.total = 3
    progress_data.save()
    sub_progress_data.total = 100
    sub_progress_data.save()

    chord(match_and_link_incoming_properties_and_taxlots.s(file_pk, progress_data.key, sub_progress_data.key), interval=15)(
        finish_matching.s(file_pk, progress_data.key))

    return progress_data.result()


@shared_task(ignore_result=True)
def finish_matching(result, import_file_id, progress_key):
    progress_data = ProgressData.from_key(progress_key)

    import_file = ImportFile.objects.get(pk=import_file_id)
    import_file.matching_done = True
    import_file.mapping_completion = 100
    import_file.matching_results_data = result
    import_file.save()

    return progress_data.finish_with_success()


def hash_state_object(obj, include_extra_data=True):
    def add_dictionary_repr_to_hash(hash_obj, dict_obj):
        assert isinstance(dict_obj, dict)

        for (key, value) in sorted(dict_obj.items(), key=lambda x_y: x_y[0]):
            if isinstance(value, dict):
                add_dictionary_repr_to_hash(hash_obj, value)
            else:
                hash_obj.update(str(unidecode(key)).encode('utf-8'))
                if isinstance(value, basestring):
                    hash_obj.update(unidecode(value).encode('utf-8'))
                else:
                    hash_obj.update(str(value).encode('utf-8'))
        return hash_obj

    def _get_field_from_obj(field_obj, field):
        if not hasattr(field_obj, field):
            return 'FOO'  # Return a random value so we can distinguish between this and None.
        else:
            return getattr(field_obj, field)

    m = hashlib.md5()
    for f in Column.retrieve_db_field_name_for_hash_comparison():
        obj_val = _get_field_from_obj(obj, f)
        m.update(f.encode('utf-8'))
        if isinstance(obj_val, datetime):
            # if this is a datetime, then make sure to save the string as a naive datetime.
            # Somehow, somewhere the data are being saved in mapping with a timezone,
            # then in matching they are removed (but the time is updated correctly)
            m.update(str(make_naive(obj_val).astimezone(tz.utc).isoformat()).encode('utf-8'))
        elif isinstance(obj_val, GEOSGeometry):
            m.update(GEOSGeometry(obj_val, srid=4326).wkt.encode('utf-8'))
        else:
            m.update(str(obj_val).encode('utf-8'))

    if include_extra_data:
        add_dictionary_repr_to_hash(m, obj.extra_data)

    return m.hexdigest()


@shared_task
def _map_additional_models(ids, file_pk, progress_key):
    """
    Create any additional models, other than properties, that could come from the
    imported file. E.g. Scenarios and Meters from a BuildingSync file.

    :param ids: chunk of property state id to process
    :param file_pk: ImportFile Primary Key
    :param progress_key: progress key
    :return:
    """
    import_file = ImportFile.objects.get(pk=file_pk)
    progress_data = ProgressData.from_key(progress_key)

    source_type_dict = {
        'Portfolio Raw': PORTFOLIO_RAW,
        'Assessed Raw': ASSESSED_RAW,
        'BuildingSync Raw': BUILDINGSYNC_RAW
    }
    source_type = source_type_dict.get(import_file.source_type, ASSESSED_RAW)

    # Don't query the org table here, just get the organization from the import_record
    org = import_file.import_record.super_organization

    # grab all property states linked to the import file and finish processing the data
    property_states = PropertyState.objects.filter(id__in=ids).prefetch_related('building_files')
    for property_state in property_states:
        if source_type == BUILDINGSYNC_RAW:
            # parse the rest of the models (scenarios, meters, etc) from the building file
            # Note that we choose _not_ to promote the property state (i.e. create a canonical property)
            # b/c that will be handled in the match/merge/linking later on
            building_file = property_state.building_files.get()
            success, property_state, _, messages = building_file.process(
                org.id,
                import_file.cycle,
                promote_property_state=False
            )

            if not success or messages.get('errors') or messages.get('warnings'):
                progress_data.add_file_info(os.path.basename(building_file.filename), messages)

    progress_data.step()

    return {
        'import_file_records': len(ids)
    }


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


def pair_new_states(merged_property_views, merged_taxlot_views, sub_progress_key):
    """
    Pair new states from lists of property views and tax lot views

    :param merged_property_views: list, merged property views
    :param merged_taxlot_views: list, merged tax lot views
    :return: None
    """
    if not merged_property_views and not merged_taxlot_views:
        return

    sub_progress_data = ProgressData.from_key(sub_progress_key)
    sub_progress_data.delete()
    sub_progress_data.total = 12
    sub_progress_data.save()

    # Not sure what the below cycle code does.
    # Commented out during Python3 upgrade.
    # cycle = chain(merged_property_views, merged_taxlot_views).next().cycle

    tax_cmp_fmt = [
        ('jurisdiction_tax_lot_id', 'custom_id_1'),
        ('ulid',),
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
    sub_progress_data.step('Pairing Data')
    tax_comparison_fields = sorted(list(set(chain.from_iterable(tax_cmp_fmt))))
    prop_comparison_fields = sorted(list(set(chain.from_iterable(prop_cmp_fmt))))

    sub_progress_data.step('Pairing Data')
    tax_comparison_field_names = list(map(lambda s: "state__{}".format(s), tax_comparison_fields))
    prop_comparison_field_names = list(map(lambda s: "state__{}".format(s), prop_comparison_fields))

    # This is a not so nice hack. but it's the only special case/field
    # that isn't on the join to the State.
    sub_progress_data.step('Pairing Data')
    tax_comparison_fields.insert(0, 'pk')
    prop_comparison_fields.insert(0, 'pk')
    tax_comparison_field_names.insert(0, 'pk')
    prop_comparison_field_names.insert(0, 'pk')

    sub_progress_data.step('Pairing Data')
    view = next(chain(merged_property_views, merged_taxlot_views))
    cycle = view.cycle
    org = view.state.organization

    global taxlot_m2m_keygen
    global property_m2m_keygen

    sub_progress_data.step('Pairing Data')
    taxlot_m2m_keygen = EquivalencePartitioner(tax_cmp_fmt, ['jurisdiction_tax_lot_id'])
    property_m2m_keygen = EquivalencePartitioner(prop_cmp_fmt,
                                                 ['pm_property_id', 'jurisdiction_property_id'])

    property_views = PropertyView.objects.filter(state__organization=org, cycle=cycle).values_list(
        *prop_comparison_field_names)
    taxlot_views = TaxLotView.objects.filter(state__organization=org, cycle=cycle).values_list(
        *tax_comparison_field_names)

    sub_progress_data.step('Pairing Data')
    # For each of the view objects, make an
    prop_type = namedtuple('Prop', prop_comparison_fields)
    taxlot_type = namedtuple('TL', tax_comparison_fields)

    sub_progress_data.step('Pairing Data')
    # Makes object with field_name->val attributes on them.
    property_objects = [prop_type(*attr) for attr in property_views]
    taxlot_objects = [taxlot_type(*attr) for attr in taxlot_views]

    # NA: I believe this is incorrect, but doing this for simplicity
    # now. The logic that is being missed is a pretty extreme corner
    # case.

    # NA: I should generate one key for each property for each thing in it's lot number state.

    # property_keys = {property_m2m_keygen.calculate_comparison_key(p): p.pk for p in property_objects}
    # taxlot_keys = [taxlot_m2m_keygen.calculate_comparison_key(tl): tl.pk for tl in taxlot_objects}

    sub_progress_data.step('Pairing Data')
    # Calculate a key for each of the split fields.
    property_keys_orig = dict(
        [(property_m2m_keygen.calculate_comparison_key(p), p.pk) for p in property_objects])

    # property_keys = copy.deepcopy(property_keys_orig)

    sub_progress_data.step('Pairing Data')
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

    sub_progress_data.step('Pairing Data')
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

    sub_progress_data.step('Pairing Data')
    for tlv in merged_taxlot_views:
        tlv_key = taxlot_m2m_keygen.calculate_comparison_key(tlv.state)
        for pv_key in property_keys:
            if property_m2m_keygen.calculate_key_equivalence(tlv_key, pv_key):
                possible_merges.append((property_keys[pv_key], taxlot_keys[tlv_key]))

    sub_progress_data.step('Pairing Data')
    for m2m in set(possible_merges):
        pv_pk, tlv_pk = m2m

        # PropertyView.objects.get(pk=pv_pk)
        # TaxLotView.objects.get(pk=tlv_pk)

        count = TaxLotProperty.objects.filter(
            property_view_id=pv_pk,
            taxlot_view_id=tlv_pk
        ).count()

        if count:
            continue

        is_primary = TaxLotProperty.objects.filter(property_view_id=pv_pk).count() == 0
        m2m_join = TaxLotProperty(
            property_view_id=pv_pk,
            taxlot_view_id=tlv_pk,
            cycle=cycle,
            primary=is_primary
        )
        m2m_join.save()

    sub_progress_data.finish_with_success()

    return


@shared_task
def _validate_use_cases(file_pk, progress_key):
    import_file = ImportFile.objects.get(pk=file_pk)
    progress_data = ProgressData.from_key(progress_key)
    progress_data.step('Validating data at buildingsync.net')
    try:
        found_version = 0

        # if this is a zip, ensure all zipped versions are the same...
        if zipfile.is_zipfile(import_file.file.name):
            with zipfile.ZipFile(import_file.file, 'r') as zip_file:
                with tempfile.TemporaryDirectory() as temp_dir:
                    zip_file.extractall(path=temp_dir)
                    for file_name in zip_file.namelist():
                        bs = BuildingSync()
                        bs.import_file(f'{temp_dir}/{file_name}')
                        if found_version == 0:
                            found_version = bs.version
                        elif found_version != bs.version:
                            raise Exception(f'Zip contains multiple BuildingSync versions (found {found_version} and {bs.version})')
            import_file.refresh_from_db()

        # it's not a zip, just get the version directly...
        else:
            bs = BuildingSync()
            bs.import_file(import_file.file)
            found_version = bs.version
        all_files_valid, file_summaries = validation_client.validate_use_case(
            import_file.file,
            filename=import_file.uploaded_filename,
            schema_version=found_version
        )
        if all_files_valid is False:
            import_file.delete()
        progress_data.finish_with_success(
            message=json.dumps({
                'valid': all_files_valid,
                'issues': file_summaries,
            }),
        )
    except validation_client.ValidationClientException as e:
        _log.debug(f'ValidationClientException while validating import_file `{file_pk}`: {e}')
        progress_data.finish_with_error(message=str(e))
        progress_data.save()
        import_file.delete()
    except Exception as e:
        _log.debug(f'Unexpected Exception while validating import_file `{file_pk}`: {e}')
        progress_data.finish_with_error(message=str(e))
        progress_data.save()
        import_file.delete()


def validate_use_cases(file_pk):
    """
    Kicks off task for validating BuildingSync files for use cases

    :param file_pk: ImportFile Primary Key
    :return:
    """
    progress_data = ProgressData(func_name='validate_use_cases', unique_id=file_pk)
    # break progress into two steps:
    # 1. started job
    # 2. finished request
    progress_data.total = 2
    progress_data.save()

    _validate_use_cases.s(file_pk, progress_data.key).apply_async()
    _log.debug(progress_data.result())
    return progress_data.result()
