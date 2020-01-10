# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

from celery import shared_task
from celery.utils.log import get_task_logger

import datetime as dt

from django.contrib.postgres.aggregates.general import ArrayAgg

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
from seed.utils.match import (
    empty_criteria_filter,
    match_merge_link,
    matching_filter_criteria,
    matching_criteria_column_names,
)
from seed.utils.merge import merge_states_with_views

_log = get_task_logger(__name__)


def log_debug(message):
    _log.debug('{}: {}'.format(message, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


@shared_task
@lock_and_track
def match_and_link_incoming_properties_and_taxlots(file_pk, progress_key):
    """
    Match incoming the properties and taxlots. Then, search for links for them.

    The process starts by identifying the incoming PropertyStates
    then TaxLotStates of an ImportFile. The steps are exactly the same for each:
        - Remove duplicates amongst the -States within the ImportFile.
        - Merge together any matches amongst the -States within the ImportFile.
        - Parse through the remaining -States to ultimately associate them
          to -Views of the current Cycle.
            - Filter duplicates of existing -States.
            - Merge incoming -States into existing -States if they match,
              keeping the existing -View.
        - For these -Views, search for matches across Cycles for linking.

    Throughout the process, the results are captured and a summary of this is
    returned as a dict.

    :param file_pk: ImportFile Primary Key
    :return results: dict
    """
    from seed.data_importer.tasks import pair_new_states

    import_file = ImportFile.objects.get(pk=file_pk)
    progress_data = ProgressData.from_key(progress_key)

    # Don't query the org table here, just get the organization from the import_record
    org = import_file.import_record.super_organization

    # Set the progress to started - 33%
    progress_data.step('Matching data')

    # Set defaults
    property_duplicates_against_existing_count = 0
    property_duplicates_within_file_count = 0
    property_merges_against_existing_count = 0
    property_merges_between_existing_count = 0
    property_merges_within_file_count = 0
    property_new_count = 0

    tax_lot_duplicates_against_existing_count = 0
    tax_lot_duplicates_within_file_count = 0
    tax_lot_merges_against_existing_count = 0
    tax_lot_merges_between_existing_count = 0
    tax_lot_merges_within_file_count = 0
    tax_lot_new_count = 0

    merged_linked_property_views = []
    merged_linked_taxlot_views = []

    # Get lists and counts of all the properties and tax lots based on the import file.
    incoming_properties = import_file.find_unmatched_property_states()
    property_initial_incoming_count = incoming_properties.count()
    incoming_tax_lots = import_file.find_unmatched_tax_lot_states()
    tax_lot_initial_incoming_count = incoming_tax_lots.count()

    if incoming_properties.exists():
        # Within the ImportFile, filter out the duplicates.
        log_debug("Start Properties filter_duplicate_states")
        promoted_property_ids, property_duplicates_within_file_count = filter_duplicate_states(
            incoming_properties
        )

        # Within the ImportFile, merge -States together based on user defined matching_criteria
        log_debug('Start Properties inclusive_match_and_merge')
        promoted_property_ids, property_merges_within_file_count = inclusive_match_and_merge(promoted_property_ids, org, PropertyState)

        # Filter Cycle-wide duplicates then merge and/or assign -States to -Views
        log_debug('Start Properties states_to_views')
        merged_property_views, property_duplicates_against_existing_count, property_new_count, property_merges_against_existing_count, property_merges_between_existing_count = states_to_views(
            promoted_property_ids,
            org,
            import_file.cycle,
            PropertyState
        )

        # Look for links across Cycles
        log_debug('Start Properties link_views')
        merged_linked_property_views = link_views(merged_property_views, PropertyView)

    if incoming_tax_lots.exists():
        # Within the ImportFile, filter out the duplicates.
        log_debug("Start TaxLots filter_duplicate_states")
        promoted_tax_lot_ids, tax_lot_duplicates_within_file_count = filter_duplicate_states(
            incoming_tax_lots
        )

        # Within the ImportFile, merge -States together based on user defined matching_criteria
        log_debug('Start TaxLots inclusive_match_and_merge')
        promoted_tax_lot_ids, tax_lot_merges_within_file_count = inclusive_match_and_merge(promoted_tax_lot_ids, org, TaxLotState)

        # Filter Cycle-wide duplicates then merge and/or assign -States to -Views
        log_debug('Start TaxLots states_to_views')
        merged_linked_taxlot_views, tax_lot_duplicates_against_existing_count, tax_lot_new_count, tax_lot_merges_against_existing_count, tax_lot_merges_between_existing_count = states_to_views(
            promoted_tax_lot_ids,
            org,
            import_file.cycle,
            TaxLotState
        )

        # Look for links across Cycles
        log_debug('Start TaxLots link_views')
        merged_linked_taxlot_views = link_views(merged_linked_taxlot_views, TaxLotView)

    log_debug('Start pair_new_states')
    progress_data.step('Pairing data')
    pair_new_states(merged_linked_property_views, merged_linked_taxlot_views)
    log_debug('End pair_new_states')

    return {
        'import_file_records': import_file.num_rows,
        'property_initial_incoming': property_initial_incoming_count,
        'property_duplicates_against_existing': property_duplicates_against_existing_count,
        'property_duplicates_within_file': property_duplicates_within_file_count,
        'property_merges_against_existing': property_merges_against_existing_count,
        'property_merges_between_existing': property_merges_between_existing_count,
        'property_merges_within_file': property_merges_within_file_count,
        'property_new': property_new_count,
        'tax_lot_initial_incoming': tax_lot_initial_incoming_count,
        'tax_lot_duplicates_against_existing': tax_lot_duplicates_against_existing_count,
        'tax_lot_duplicates_within_file': tax_lot_duplicates_within_file_count,
        'tax_lot_merges_against_existing': tax_lot_merges_against_existing_count,
        'tax_lot_merges_between_existing': tax_lot_merges_between_existing_count,
        'tax_lot_merges_within_file': tax_lot_merges_within_file_count,
        'tax_lot_new': tax_lot_new_count,
    }


def filter_duplicate_states(unmatched_states):
    """
    Takes a QuerySet of -States and flags then separates exact duplicates. This
    method returns two items:
        - list of IDs of unique -States + IDs for representative -States of duplicates
        - count of duplicates that were filtered out of the original set

    Sets of IDs for duplicate -States are captured in lists.

    The list being returned is created by taking one member of each of
    the duplicate sets. The IDs that were not taken are used to
    flag the corresponding -States with DATA_STATE_DELETE.

    :param unmatched_states: QS
    :return: canonical_state_ids, duplicate_count
    """

    ids_grouped_by_hash = unmatched_states.\
        values('hash_object').\
        annotate(duplicate_sets=ArrayAgg('id')).\
        values_list('duplicate_sets', flat=True)

    # For consistency, take the first member of each of the duplicate sets
    canonical_state_ids = [
        ids.pop(ids.index(min(ids)))
        for ids
        in ids_grouped_by_hash
    ]
    duplicate_state_ids = reduce(lambda x, y: x + y, ids_grouped_by_hash)
    duplicate_count = unmatched_states.filter(pk__in=duplicate_state_ids).update(data_state=DATA_STATE_DELETE)

    return canonical_state_ids, duplicate_count


def inclusive_match_and_merge(unmatched_state_ids, org, StateClass):
    """
    Takes a list of unmatched_state_ids, combines matches of the corresponding
    -States, and returns a set of IDs of the remaining -States.

    :param unmatched_states_ids: list
    :param org: Organization object
    :param StateClass: PropertyState or TaxLotState
    :return: promoted_ids: list
    """
    column_names = matching_criteria_column_names(org.id, StateClass.__name__)

    # IDs of -States with all matching criteria equal to None are intially promoted
    # as they're not eligible for matching.
    promoted_ids = list(
        StateClass.objects.filter(
            pk__in=unmatched_state_ids,
            **empty_criteria_filter(StateClass, column_names)
        ).values_list('id', flat=True)
    )

    # Update the list of IDs whose states haven't been checked for matches.
    unmatched_state_ids = list(
        set(unmatched_state_ids) - set(promoted_ids)
    )

    # Group IDs by -States that match each other
    matched_id_groups = StateClass.objects.\
        filter(id__in=unmatched_state_ids).\
        values(*column_names).\
        annotate(matched_ids=ArrayAgg('id')).\
        values_list('matched_ids', flat=True)

    # Collapse groups of matches found in the previous step into 1 -State per group
    merges_within_file = 0
    priorities = Column.retrieve_priorities(org)
    for ids in matched_id_groups:
        if len(ids) == 1:
            # If there's only 1, no merging is needed, so just promote the ID.
            promoted_ids += ids
        else:
            states = [s for s in StateClass.objects.filter(pk__in=ids).order_by('-id')]
            merge_state = states.pop()

            merges_within_file += len(states)

            while len(states) > 0:
                newer_state = states.pop()
                merge_state = save_state_match(merge_state, newer_state, priorities)

            promoted_ids.append(merge_state.id)

    # Flag the soon to be promoted ID -States as having gone through matching
    StateClass.objects.filter(pk__in=promoted_ids).update(data_state=DATA_STATE_MATCHING)

    return promoted_ids, merges_within_file


def states_to_views(unmatched_state_ids, org, cycle, StateClass):
    """
    The purpose of this method is to take incoming -States and, apply them to a
    -View. In the process of doing so, -States could be flagged for "deletion"
    (and not applied to a -View), merged with existing -States, or found to be
    brand new. Regardless, the goal is to ultimately associate -States to -Views.

    For incoming -States needing to be matched to an existing -State, merge
    them and take the existing -State's -View to be the -View for the new merged
    state.

    For directly promote-able -States, a new -View and canonical object
    (Property or TaxLot) are created for it.

    :param unmatched_states: list
    :param org: Organization object
    :param cycle: Cycle object
    :param StateClass: PropertyState or TaxLotState
    :return: processed_views, duplicate_count, new + matched counts
    """
    table_name = StateClass.__name__

    if table_name == 'PropertyState':
        ViewClass = PropertyView
    elif table_name == 'TaxLotState':
        ViewClass = TaxLotView

    # Identify existing used -States
    existing_cycle_views = ViewClass.objects.filter(cycle_id=cycle)
    existing_states = StateClass.objects.filter(
        pk__in=Subquery(existing_cycle_views.values('state_id'))
    )

    # Apply DATA_STATE_DELETE to incoming duplicate -States of existing -States in Cycle
    duplicate_states = StateClass.objects.filter(
        pk__in=unmatched_state_ids,
        hash_object__in=Subquery(existing_states.values('hash_object'))
    )
    duplicate_count = duplicate_states.update(data_state=DATA_STATE_DELETE)

    column_names = matching_criteria_column_names(org.id, table_name)

    # For the remaining incoming -States (filtering those duplicates), identify
    # -States with all matching criteria being None. These aren't eligible for matching.
    empty_matching_criteria = empty_criteria_filter(StateClass, column_names)
    promote_states = StateClass.objects.filter(
        pk__in=unmatched_state_ids,
        **empty_matching_criteria
    ).exclude(pk__in=Subquery(duplicate_states.values('id')))

    # Identify and filter out -States that have been "handled".
    handled_states = promote_states | duplicate_states
    unmatched_states = StateClass.objects.filter(pk__in=unmatched_state_ids).exclude(
        pk__in=Subquery(handled_states.values('id'))
    )

    # For the remaining -States, search for a match within the -States that are attached to -Views.
    # If one match is found, pass that along.
    # If multiple matches are found, merge them together, pass along the resulting record.
    # Otherwise, add current -State to be promoted as is.
    merged_between_existing_count = 0
    merge_state_pairs = []
    for state in unmatched_states:
        matching_criteria = matching_filter_criteria(state, column_names)
        existing_state_matches = StateClass.objects.filter(
            pk__in=Subquery(existing_cycle_views.values('state_id')),
            **matching_criteria
        )
        count = existing_state_matches.count()

        if count > 1:
            merged_between_existing_count += count
            existing_state_ids = list(existing_state_matches.order_by('updated').values_list('id', flat=True))
            # The following merge action ignores merge protection and prioritizes -States by most recent AuditLog
            merged_state = merge_states_with_views(existing_state_ids, org.id, 'System Match', StateClass)
            merge_state_pairs.append((merged_state, state))
        elif count == 1:
            merge_state_pairs.append((existing_state_matches.first(), state))
        else:
            promote_states = promote_states | StateClass.objects.filter(pk=state.id)

    # Process -States into -Views either directly (promoted_ids) or post-merge (merge_state_pairs).
    _log.debug("There are %s merge_state_pairs and %s promote_states" % (len(merge_state_pairs), promote_states.count()))
    priorities = Column.retrieve_priorities(org.pk)
    processed_views = []
    promoted_ids = []
    merged_state_ids = []
    try:
        with transaction.atomic():
            for state_pair in merge_state_pairs:
                existing_state, newer_state = state_pair
                existing_view = ViewClass.objects.get(state_id=existing_state.id)

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

    new_count = len(promoted_ids)
    # update merge_state while excluding any states that were a product of a previous, file-inclusive merge
    StateClass.objects.filter(pk__in=promoted_ids).exclude(merge_state=MERGE_STATE_MERGED).update(
        merge_state=MERGE_STATE_NEW
    )
    matched_count = StateClass.objects.filter(pk__in=merged_state_ids).update(
        data_state=DATA_STATE_MATCHING,
        merge_state=MERGE_STATE_MERGED
    )

    return list(set(processed_views)), duplicate_count, new_count, matched_count, merged_between_existing_count


def link_views(merged_views, ViewClass):
    """
    Run each of the given -Views through a linking round.

    For details on the actual linking logic, please refer to the the
    match_merge_link() method.
    """
    if ViewClass == PropertyView:
        state_class_name = "PropertyState"
    else:
        state_class_name = "TaxLotState"

    processed_views = []
    for view in merged_views:
        _merge_count, _link_count, view_id = match_merge_link(view.id, state_class_name)

        if view_id is not None:
            processed_views.append(ViewClass.objects.get(pk=view_id))
        else:
            processed_views.append(view)

    return processed_views


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
