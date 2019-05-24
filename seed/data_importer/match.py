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
from django.db.models import Subquery

from functools import reduce

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


def log_debug(message):
    _log.debug('{}: {}'.format(message, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


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

    # Set the progress to started - 33%
    progress_data.step('Matching data')

    # Set defaults
    file_duplicate_property_count = 0
    file_duplicate_tax_lot_count = 0
    existing_duplicate_property_count = 0
    existing_duplicate_tax_lot_count = 0
    new_property_count = 0
    new_tax_lot_count = 0
    merged_property_views = []
    merged_taxlot_views = []

    # Get lists of all the properties and tax lots based on the import file.
    incoming_properties = import_file.find_unmatched_property_states()
    incoming_tax_lots = import_file.find_unmatched_tax_lot_states()

    if incoming_properties.exists():
        # Within the ImportFile, filter out the duplicates.
        log_debug("Start Properties filter_duplicate_states")
        unmatched_property_ids, file_duplicate_property_count = filter_duplicate_states(
            incoming_properties
        )

        # Within the ImportFile, merge -States together based on user defined matching_criteria
        log_debug('Start Properties inclusive_match_and_merge')
        unmatched_property_ids = inclusive_match_and_merge(unmatched_property_ids, org, PropertyState)

        # Filter Cycle-wide duplicates then merge and/or assign -States to -Views
        log_debug('Start Properties states_to_views')
        merged_property_views, existing_duplicate_property_count, new_property_count = states_to_views(
            unmatched_property_ids,
            org,
            import_file.cycle,
            PropertyState
        )

    if incoming_tax_lots.exists():
        # Within the ImportFile, filter out the duplicates.
        log_debug("Start TaxLots filter_duplicate_states")
        unmatched_tax_lot_ids, file_duplicate_tax_lot_count = filter_duplicate_states(
            incoming_tax_lots)

        # Within the ImportFile, merge -States together based on user defined matching_criteria
        log_debug('Start TaxLots inclusive_match_and_merge')
        unmatched_tax_lot_ids = inclusive_match_and_merge(unmatched_tax_lot_ids, org, TaxLotState)

        # Filter Cycle-wide duplicates then merge and/or assign -States to -Views
        log_debug('Start TaxLots states_to_views')
        merged_taxlot_views, existing_duplicate_tax_lot_count, new_tax_lot_count = states_to_views(
            unmatched_tax_lot_ids,
            org,
            import_file.cycle,
            TaxLotState
        )

    log_debug('Start pair_new_states')
    progress_data.step('Pairing data')
    pair_new_states(merged_property_views, merged_taxlot_views)
    log_debug('End pair_new_states')

    return {
        'import_file_records': import_file.num_rows,
        'property_all_unmatched': incoming_properties.count(),
        'property_duplicates': file_duplicate_property_count,
        'property_duplicates_of_existing': existing_duplicate_property_count,
        'property_unmatched': new_property_count,
        'tax_lot_all_unmatched': incoming_tax_lots.count(),
        'tax_lot_duplicates': file_duplicate_tax_lot_count,
        'tax_lot_duplicates_of_existing': existing_duplicate_tax_lot_count,
        'tax_lot_unmatched': new_tax_lot_count,
    }


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
    duplicate_count = unmatched_states.filter(pk__in=duplicate_state_ids).update(data_state=DATA_STATE_DELETE)

    return canonical_state_ids, duplicate_count


# from seed.utils.cprofile import cprofile
# @cprofile()
def inclusive_match_and_merge(unmatched_state_ids, org, ObjectStateClass):
    """
    Take a list of unmatched_property_states or unmatched_tax_lot_states and returns a set of
    states that correspond to unmatched states.

    :param unmatched_states: list, PropertyStates or TaxLotStates
    :param partitioner: instance of EquivalencePartitioner
    :return: [list, list], merged_objects, equivalence_classes keys
    """
    table_name = ObjectStateClass.__name__

    promoted_ids = list(
        _empty_criteria_states_qs(
            unmatched_state_ids,
            org.id,
            ObjectStateClass
        ).values_list('id', flat=True)
    )

    unmatched_state_ids = list(
        set(unmatched_state_ids) - set(promoted_ids)
    )

    matching_states = []
    while unmatched_state_ids:
        state_id = unmatched_state_ids.pop()
        state = ObjectStateClass.objects.get(pk=state_id)

        matching_criteria = _matching_filter_criteria(org.id, table_name, state)
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

    priorities = Column.retrieve_priorities(org)
    for states in matching_states:
        states = list(states)
        merge_state = states.pop()

        while len(states) > 0:
            newer_state = states.pop()
            merge_state = save_state_match(merge_state, newer_state, priorities)

        promoted_ids.append(merge_state.id)

    ObjectStateClass.objects.filter(pk__in=promoted_ids).update(data_state=DATA_STATE_MATCHING)

    return promoted_ids


# @cprofile(n=50)
def states_to_views(unmatched_state_ids, org, cycle, ObjectStateClass):
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
    table_name = ObjectStateClass.__name__

    if table_name == 'PropertyState':
        ObjectViewClass = PropertyView
    elif table_name == 'TaxLotState':
        ObjectViewClass = TaxLotView

    existing_cycle_views = ObjectViewClass.objects.filter(cycle_id=cycle)

    # Apply DATA_STATE_DELETE to incoming duplicate -States of existing -States in Cycle
    existing_states = ObjectStateClass.objects.filter(pk__in=Subquery(existing_cycle_views.values('state_id')))
    duplicate_states = ObjectStateClass.objects.filter(
        pk__in=unmatched_state_ids,
        hash_object__in=Subquery(existing_states.values('hash_object'))
    )
    duplicate_count = duplicate_states.update(data_state=DATA_STATE_DELETE)

    # For the remaining incoming -States (filtering those duplicates), identify -States with matches
    promote_states = _empty_criteria_states_qs(
        unmatched_state_ids,
        org.id,
        ObjectStateClass
    ).exclude(pk__in=Subquery(duplicate_states.values('id')))

    # Comment
    handled_states = promote_states | duplicate_states
    unmatched_states = ObjectStateClass.objects.filter(pk__in=unmatched_state_ids).exclude(
        pk__in=Subquery(handled_states.values('id'))
    )

    merge_state_pairs = []
    for state in unmatched_states:
        matching_criteria = _matching_filter_criteria(org.id, table_name, state)
        state_match = ObjectStateClass.objects.filter(
            pk__in=Subquery(existing_cycle_views.values('state_id')),
            **matching_criteria
        )

        if state_match.exists() and any(v is not None for v in matching_criteria.values()):
            merge_state_pairs.append((state_match.first(), state))
        else:
            promote_states = promote_states | ObjectStateClass.objects.filter(pk=state.id)

    # Process -States into -Views
    _log.debug("There are %s merge_state_pairs and %s promote_states" % (len(merge_state_pairs), len(promote_states)))
    processed_views = []
    priorities = Column.retrieve_priorities(org.pk)
    promoted_ids = []
    merged_state_ids = []
    try:
        with transaction.atomic():
            for state_pair in merge_state_pairs:
                existing_state, newer_state = state_pair
                existing_view = ObjectViewClass.objects.get(state_id=existing_state.id)

                # Merge -States and assign new/merged -State to existing -View
                merged_state = save_state_match(existing_state, newer_state, priorities)
                existing_view.state = merged_state
                existing_view.save()

                processed_views.append(existing_view)
                merged_state_ids.append(merged_state.id)

            for state in promote_states:
                promoted_ids.append(state.id)
                created_view = state.promote(cycle)
                processed_views.append(created_view)
    except IntegrityError as e:
        raise IntegrityError("Could not merge results with error: %s" % (e))

    new_count = ObjectStateClass.objects.filter(pk__in=promoted_ids).exclude(merge_state=MERGE_STATE_MERGED).update(
        merge_state=MERGE_STATE_NEW
    )
    matched_count = ObjectStateClass.objects.filter(pk__in=merged_state_ids).update(
        data_state=DATA_STATE_MATCHING,
        merge_state=MERGE_STATE_MERGED
    )

    return list(set(processed_views)), duplicate_count, new_count + matched_count


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


def _empty_criteria_states_qs(state_ids, organization_id, ObjectStateClass):
    empty_state = ObjectStateClass()
    empty_criteria_filter = _matching_filter_criteria(
        organization_id,
        ObjectStateClass.__name__,
        empty_state
    )

    return ObjectStateClass.objects.filter(
        pk__in=state_ids,
        **empty_criteria_filter
    )


def _matching_filter_criteria(organization_id, table_name, state):
    return {
        column_name: getattr(state, column_name, None)
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
