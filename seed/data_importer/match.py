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

from itertools import chain
# from seed.data_importer.equivalence_partitioner import EquivalencePartitioner
from seed.data_importer.models import (
    ImportFile,
    # ImportRecord,
    # STATUS_READY_TO_MERGE,
)
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


# @cprofile(n=50)
def merge_unmatched_into_views(unmatched_states, org, import_file):
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
    organization = unmatched_states[0].organization
    table_name = type(unmatched_states[0]).__name__

    if table_name == 'PropertyState':
        ObjectStateClass = PropertyState
        ObjectViewClass = PropertyView
        # ParentAttrName = "property"
    elif table_name == 'TaxLotState':
        ObjectStateClass = TaxLotState
        ObjectViewClass = TaxLotView
        # ParentAttrName = "taxlot"
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
def match_and_merge_unmatched_objects(unmatched_states):
    """
    Take a list of unmatched_property_states or unmatched_tax_lot_states and returns a set of
    states that correspond to unmatched states.

    :param unmatched_states: list, PropertyStates or TaxLotStates
    :param partitioner: instance of EquivalencePartitioner
    :return: [list, list], merged_objects, equivalence_classes keys
    """
    organization = unmatched_states[0].organization
    table_name = type(unmatched_states[0]).__name__

    # Collect matching criteria columns while replacing address_line_1 with
    # normalized_address if applicable. No errors if normalized_address shows up
    # twice, which shouldn't really happen anyway.
    matching_criteria_column_names = [
        'normalized_address' if c.column_name == "address_line_1" else c.column_name
        for c
        in Column.objects.filter(
            organization_id=organization.id,
            is_matching_criteria=True,
            table_name=table_name
        )
    ]

    merged_objects = []
    unmatched_ids = defaultdict(list)
    # Iterate through sorted -States (by ascending PK) ensuring precedence is
    # given to newer state on merges done later.
    for state in sorted(unmatched_states, key=lambda state: -getattr(state, "pk", None)):
        matching_criteria_values = tuple(
            getattr(
                state,
                column_name,
                state.extra_data.get(column_name, None)
            )
            for column_name
            in matching_criteria_column_names
        )

        # If values are all None append -State to return list
        if all(value is None for value in matching_criteria_values):
            merged_objects.append(state)
        else:
            unmatched_ids[matching_criteria_values].append(state)

    priorities = Column.retrieve_priorities(organization)
    for ids in unmatched_ids.values():
        merge_state = ids.pop()

        while len(ids) > 0:
            newer_state = ids.pop()  # This is newer due to the previous sort by PK
            merge_state = save_state_match(merge_state, newer_state, priorities)

        merged_objects.append(merge_state)

    return merged_objects


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

    hash_values = []
    for unmatch in unmatched_states:
        hash_values.append(unmatch.hash_object)
    equality_classes = defaultdict(list)

    for (ndx, hashval) in enumerate(hash_values):
        equality_classes[hashval].append(ndx)

    canonical_states = [unmatched_states[equality_list[0]] for equality_list in
                        equality_classes.values()]
    canonical_state_ids = set([s.pk for s in canonical_states])
    noncanonical_states = [u for u in unmatched_states if u.pk not in canonical_state_ids]

    return canonical_states, noncanonical_states


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
        _log.debug("Start filter_duplicated_states: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        unmatched_properties, duplicate_property_states = filter_duplicated_states(
            all_unmatched_properties
        )
        _log.debug("End filter_duplicated_states: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner, while ignoring duplicates.
        _log.debug("Start match_and_merge_unmatched_objects: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        unmatched_properties = match_and_merge_unmatched_objects(unmatched_properties)
        _log.debug("End match_and_merge_unmatched_objects: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        # TODO #239: This is quite slow... fix this next
        _log.debug("Start merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        merged_property_views = merge_unmatched_into_views(
            unmatched_properties,
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

        # Merge everything together based on the notion of equivalence
        # provided by the partitioner.
        unmatched_tax_lots = match_and_merge_unmatched_objects(unmatched_tax_lots)

        # Take the final merged-on-import objects, and find Views that
        # correspond to it and merge those together.
        _log.debug("Start tax_lot merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"))
        merged_taxlot_views = merge_unmatched_into_views(
            unmatched_tax_lots,
            org,
            import_file
        )
        _log.debug("End tax_lot merge_unmatched_into_views: %s" % dt.datetime.now().strftime(
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

    for state in chain(duplicate_property_states, duplicate_tax_lot_states):
        state.data_state = DATA_STATE_DELETE
        # state.merge_state = MERGE_STATE_DUPLICATE
        state.save()

    return {
        'import_file_records': import_file.num_rows,
        'property_all_unmatched': len(all_unmatched_properties),
        'property_duplicates': len(duplicate_property_states),
        'property_duplicates_of_existing': len(duplicates_of_existing_property_states),
        'property_unmatched': len(unmatched_properties),
        'tax_lot_all_unmatched': len(all_unmatched_tax_lots),
        'tax_lot_duplicates': len(duplicate_tax_lot_states),
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
