# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from celery import shared_task
from celery.utils.log import get_task_logger

from collections import defaultdict

import datetime as dt

from django.db import (
    IntegrityError,
    transaction,
)

from functools import reduce

from itertools import chain
from seed.data_importer.models import ImportFile
from seed.decorators import lock_and_track
from seed.lib.merging import merging
from seed.lib.progress_data.progress_data import ProgressData
from seed.models import (
    DATA_STATE_DELETE,
    DATA_STATE_MAPPING,
    DATA_STATE_MATCHING,
    DATA_STATE_UNKNOWN,
    MERGE_STATE_MERGED,
    MERGE_STATE_NEW,
    MERGE_STATE_UNKNOWN,
    Column,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView,
)
from seed.models.auditlog import AUDIT_IMPORT

_log = get_task_logger(__name__)


def filter_duplicate_states(unmatched_states):
    """
    Takes a QuerySet of -States, where some records are exact duplicates of
    others. This method returns two lists:
        - IDs of unique -States + IDs for representative -States of duplicates
        - IDs of duplicate -States not chosen to represent their set of duplicates

    This is done by constructing a dictionary where the keys are hash_objects
    and the values are lists of IDs of -States with that hash_object.

    The first list being returned is created by taking one member of each of
    the dictionary values (list of IDs). The second is created by combining the
    remaining dictionary values into one list.

    :param unmatched_states: QuerySet, unmatched states
    :return: canonical_state_ids, duplicate_state_ids
    """

    hash_object_ids = defaultdict(list)
    for unmatched in unmatched_states:
        hash_object_ids[unmatched.hash_object].append(unmatched.pk)

    ids_grouped_by_hash = hash_object_ids.values()
    canonical_state_ids = [ids.pop() for ids in ids_grouped_by_hash]
    duplicate_state_ids = reduce(lambda x, y: x + y, ids_grouped_by_hash)

    return canonical_state_ids, duplicate_state_ids


# @cprofile(n=50)
def merge_unmatched_into_views(unmatched_state_ids, org, import_file, ObjectStateClass):
    """
    This is fairly inefficient, because we grab all the organization's entire PropertyViews at once.
    Surely this can be improved, but the logic is unusual/particularly dynamic here, so hopefully
    this can be refactored into a better, purely database approach... Perhaps existing_view_states
    can wrap database calls. Still the abstractions are subtly different (can I refactor the
    partitioner to use Query objects); it may require a bit of thinking.

    :param unmatched_states:
    :param partitioner:
    :param org:
    :param import_file:
    :return:
    """

    # Cycle coming from the import_file does not make sense here.
    # Makes testing hard. Should be an argument.
    current_match_cycle = import_file.cycle
    organization = org
    table_name = ObjectStateClass.__name__
    unmatched_states = ObjectStateClass.objects.filter(pk__in=unmatched_state_ids)

    if table_name == 'PropertyState':
        ObjectViewClass = PropertyView
    elif table_name == 'TaxLotState':
        ObjectViewClass = TaxLotView
    else:
        raise ValueError("Unknown class '{}' passed to merge_unmatched_into_views".format(
            type(unmatched_states[0])))

    matching_criteria_column_names = [
        'normalized_address' if c.column_name == "address_line_1" else c.column_name
        for c
        in Column.objects.filter(
            organization_id=organization.id,
            is_matching_criteria=True,
            table_name=table_name
        )
    ]

    state_ids_from_views = [
        view.state_id
        for view
        in ObjectViewClass.objects.filter(
            state__organization=organization,
            cycle_id=current_match_cycle
        )
    ]

    merge_data = []
    promote_data = []
    for state in unmatched_states:
        if PropertyState.objects.filter(id__in=state_ids_from_views, hash_object=state.hash_object).exists():
            state.data_state = DATA_STATE_DELETE
            state.save()
            continue

        matching_criteria = {
            (column if hasattr(state, column) else 'extra_data__{}'.format(column)): (getattr(state, column, None) if hasattr(state, column) else state.extra_data.get(column, None))
            for column
            in matching_criteria_column_names
        }
        state_match = ObjectStateClass.objects.filter(id__in=state_ids_from_views, **matching_criteria)

        if state_match.exists() and any(v is not None for v in matching_criteria.values()):
            merge_data.append((state_match.first(), state))
            continue

        promote_data.append([state, current_match_cycle])

    # _log.debug("There are %s merge_data and %s promote_data" % (len(merge_data), len(promote_data)))
    matched_views = []  # this gets passed at the end. seems to be the views that have been updated
    priorities = Column.retrieve_priorities(organization.pk)
    try:
        with transaction.atomic():
            for datum in merge_data:
                existing_state, newer_state = datum
                initial_view = ObjectViewClass.objects.get(state_id=existing_state.id)

                initial_view.state = save_state_match(existing_state, newer_state, priorities)
                initial_view.save()

                matched_views.append(initial_view)

            for promote_datum in promote_data:
                created_view = promote_datum[0].promote(promote_datum[1])
                matched_views.append(created_view)
    except IntegrityError as e:
        raise IntegrityError("Could not merge results with error: %s" % (e))

    return list(set(matched_views))


# from seed.utils.cprofile import cprofile
# @cprofile()
def match_and_merge_unmatched_objects(unmatched_state_ids, ObjectStateClass):
    """
    Take a list of unmatched_property_states or unmatched_tax_lot_states and returns a set of
    states that correspond to unmatched states.

    :param unmatched_states: list, PropertyStates or TaxLotStates
    :param partitioner: instance of EquivalencePartitioner
    :return: [list, list], merged_objects, equivalence_classes keys
    """
    example_state = ObjectStateClass.objects.get(pk=unmatched_state_ids[0])
    organization = example_state.organization
    table_name = ObjectStateClass.__name__

    promoted_ids = _empty_criteria_ids(unmatched_state_ids, example_state, ObjectStateClass, table_name)
    unmatched_state_ids = list(
        set(unmatched_state_ids) - set(promoted_ids)
    )

    matching_states = []
    while unmatched_state_ids:
        state_id = unmatched_state_ids.pop()
        state = ObjectStateClass.objects.get(pk=state_id)

        matching_criteria = _matching_filter_criteria(organization.id, table_name, state)
        state_matches = ObjectStateClass.objects.filter(
            id__in=unmatched_state_ids + [state_id],
            **matching_criteria
        ).order_by('-id')

        if state_matches.exists():
            matching_states.append(state_matches)
            unmatched_state_ids = list(
                set(unmatched_state_ids) - set(state_matches.values_list('id', flat=True))
            )
        else:
            promoted_ids.append(state.id)

    priorities = Column.retrieve_priorities(organization)
    for states in matching_states:
        states = list(states)
        merge_state = states.pop()

        while len(states) > 0:
            newer_state = states.pop()
            merge_state = save_state_match(merge_state, newer_state, priorities)

        promoted_ids.append(merge_state.id)

    return promoted_ids


@shared_task
@lock_and_track
# @cprofile()
def match_properties_and_taxlots(file_pk, progress_key):
    """
    Match the properties and taxlots

    :param file_pk: ImportFile Primary Key
    :return:
    """
    from seed.data_importer.tasks import pair_new_states

    import_file = ImportFile.objects.get(pk=file_pk)
    progress_data = ProgressData.from_key(progress_key)

    # Don't query the org table here, just get the organization from the import_record
    org = import_file.import_record.super_organization

    # Return a list of all the properties/tax lots based on the import file.
    all_unmatched_properties = import_file.find_unmatched_property_states()

    # Set the progress to started - 33%
    progress_data.step('Matching data')

    unmatched_properties = []
    unmatched_tax_lots = []
    duplicates_of_existing_property_states = []
    duplicates_of_existing_taxlot_states = []
    if all_unmatched_properties:
        # Filter out the duplicates within the import file.
        _log.debug("Start filter_duplicate_states: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        unmatched_property_ids, duplicate_property_state_ids = filter_duplicate_states(
            all_unmatched_properties
        )
        _log.debug("End filter_duplicate_states: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner, while ignoring duplicates.
        _log.debug("Start match_and_merge_unmatched_objects: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        unmatched_property_ids = match_and_merge_unmatched_objects(unmatched_property_ids, PropertyState)
        _log.debug("End match_and_merge_unmatched_objects: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        # TODO #239: This is quite slow... fix this next
        _log.debug("Start merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        merged_property_views = merge_unmatched_into_views(
            unmatched_property_ids,
            org,
            import_file,
            PropertyState
        )
        _log.debug(
            "End merge_unmatched_into_views: %s" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # Filter out the exact duplicates found in the previous step
        duplicates_of_existing_property_states = [state for state in unmatched_properties if
                                                  state.data_state == DATA_STATE_DELETE]
        unmatched_properties = [state for state in unmatched_properties
                                if state not in duplicates_of_existing_property_states]
    else:
        duplicate_property_state_ids = []
        merged_property_views = []

    # Do the same process with the TaxLots.
    all_unmatched_tax_lots = import_file.find_unmatched_tax_lot_states()

    if all_unmatched_tax_lots:
        # Filter out the duplicates.  Do we actually want to delete them
        # here?  Mark their abandonment in the Audit Logs?
        unmatched_tax_lot_ids, duplicate_tax_lot_state_ids = filter_duplicate_states(
            all_unmatched_tax_lots)

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner.
        unmatched_tax_lot_ids = match_and_merge_unmatched_objects(unmatched_tax_lot_ids, TaxLotState)

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        _log.debug("Start tax_lot merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        merged_taxlot_views = merge_unmatched_into_views(
            unmatched_tax_lot_ids,
            org,
            import_file,
            TaxLotState
        )
        _log.debug("End tax_lot merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Filter out the exact duplicates found in the previous step
        duplicates_of_existing_taxlot_states = [state for state in unmatched_tax_lots
                                                if state.data_state == DATA_STATE_DELETE]
        unmatched_tax_lots = [state for state in unmatched_tax_lots if
                              state not in duplicates_of_existing_taxlot_states]
    else:
        duplicate_tax_lot_state_ids = []
        merged_taxlot_views = []

    # TODO #239: This is the next slowest... fix me too.
    _log.debug("Start pair_new_states: %s" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    progress_data.step('Pairing data')
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

    PropertyState.objects.filter(pk__in=duplicate_property_state_ids).update(data_state=DATA_STATE_DELETE)
    TaxLotState.objects.filter(pk__in=duplicate_tax_lot_state_ids).update(data_state=DATA_STATE_DELETE)

    return {
        'import_file_records': import_file.num_rows,
        'property_all_unmatched': len(all_unmatched_properties),
        'property_duplicates': len(duplicate_property_state_ids),
        'property_duplicates_of_existing': len(duplicates_of_existing_property_states),
        'property_unmatched': len(unmatched_properties),
        'tax_lot_all_unmatched': len(all_unmatched_tax_lots),
        'tax_lot_duplicates': len(duplicate_tax_lot_state_ids),
        'tax_lot_duplicates_of_existing': len(duplicates_of_existing_taxlot_states),
        'tax_lot_unmatched': len(unmatched_tax_lots),
    }


def save_state_match(state1, state2, priorities):
    """
    Merge the contents of state2 into state1

    :param state1: PropertyState or TaxLotState
    :param state2: PropertyState or TaxLotState
    :param priorities: dict, column names and the priorities of the merging of data. This includes
    all of the priorites for the columns, not just the priorities for the selected taxlotstate.
    :return: state1, after merge
    """
    merged_state = type(state1).objects.create(organization=state1.organization)

    merged_state = merging.merge_state(
        merged_state, state1, state2, priorities[merged_state.__class__.__name__]
    )

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


def _empty_criteria_ids(unmatched_state_ids, example_state, ObjectStateClass, table_name):
    empty_criteria_filter = {
        '{}__isnull'.format(_filter_column_name(example_state, column_name)): True
        for column_name
        in _matching_criteria_column_names(example_state.organization_id, table_name)
    }
    return list(
        ObjectStateClass.objects.filter(
            pk__in=unmatched_state_ids,
            **empty_criteria_filter
        ).values_list('id', flat=True)
    )

def _matching_filter_criteria(organization_id, table_name, state):
    return {
        _filter_column_name(state, column_name): _filter_column_value(state, column_name)
        for column_name
        in _matching_criteria_column_names(organization_id, table_name)
    }


def _matching_criteria_column_names(organization_id, table_name):
    """
    Collect matching criteria columns while replacing address_line_1 with
    normalized_address if applicable. A Python set is returned to handle the
    case where normalized_address might show up twice, which shouldn't really
    happen anyway.
    """
    return {
        'normalized_address' if c.column_name == "address_line_1" else c.column_name
        for c
        in Column.objects.filter(
            organization_id=organization_id,
            is_matching_criteria=True,
            table_name=table_name
        )
    }


def _filter_column_name(state, column_name):
    if hasattr(state, column_name):
        return column_name
    else:
        return 'extra_data__{}'.format(column_name)


def _filter_column_value(state, column_name):
    return getattr(
        state,
        column_name,
        state.extra_data.get(column_name, None)
    )
