"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import datetime as dt
import math
from collections import defaultdict
from typing import Union

from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import IntegrityError, transaction
from django.db.models import Subquery

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
    Cycle,
    PropertyAuditLog,
    PropertyState,
    PropertyView,
    PropertyViewLabel,
    StatusLabel,
    TaxLotAuditLog,
    TaxLotState,
    TaxLotView,
)
from seed.models.auditlog import AUDIT_IMPORT
from seed.utils.match import (
    MultipleALIError,
    NoAccessError,
    NoViewsError,
    _get_ali,
    _link_matches,
    empty_criteria_filter,
    get_matching_criteria_column_names,
    matching_filter_criteria,
    update_sub_progress_total,
)
from seed.utils.merge import merge_states_with_views
from seed.utils.ubid import get_jaccard_index, merge_ubid_models

_log = get_task_logger(__name__)


def log_debug(message):
    _log.debug("{}: {}".format(message, dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


@shared_task
@lock_and_track
def match_and_link_incoming_properties_and_taxlots(file_pk, progress_key, sub_progress_key, property_state_ids_by_cycle=None):
    """
    Utilizes the helper function match_and_link_incoming_properties_and_taxlots_by_cycle

    :param file_pk: ImportFile Primary Key
    :param property_state_ids_by_cycle: A dictionary with cycle ids as the keys, used for multi-cycle-uploads
    and an array of associated property states as the values
    :return results: dict
    """

    import_file = ImportFile.objects.get(pk=file_pk)
    org = import_file.import_record.super_organization

    if property_state_ids_by_cycle is None:
        # Get lists and counts of all the properties and tax lots based on the import file.
        incoming_properties = import_file.find_unmatched_property_states()
        incoming_tax_lots = import_file.find_unmatched_tax_lot_states()
        cycle = import_file.cycle

        results = match_and_link_incoming_properties_and_taxlots_by_cycle(
            file_pk, progress_key, sub_progress_key, incoming_properties, incoming_tax_lots, cycle
        )

    else:
        results_list = []
        for cycle_id, property_state_ids in property_state_ids_by_cycle.items():
            # Get lists and counts of all the properties and tax lots based on the import file.
            incoming_properties = PropertyState.objects.filter(pk__in=property_state_ids, organization=org)
            incoming_tax_lots = import_file.find_unmatched_tax_lot_states()

            cycle = Cycle.objects.get(id=cycle_id)
            results_list.append(
                match_and_link_incoming_properties_and_taxlots_by_cycle(
                    file_pk, progress_key, sub_progress_key, incoming_properties, incoming_tax_lots, cycle
                )
            )

        # combine array of dictionaries in results_list into results
        results = {}
        for dict in results_list:
            for key, value in dict.items():
                results[key] = results.get(key, 0) + value

    results["import_file_records"] = import_file.num_rows

    return results


def match_and_link_incoming_properties_and_taxlots_by_cycle(
    file_pk, progress_key, sub_progress_key, incoming_properties, incoming_tax_lots, cycle
):
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
    :param cycle: cycle object
    :return results: dict
    """
    from seed.data_importer.tasks import pair_new_states

    import_file = ImportFile.objects.get(pk=file_pk)
    progress_data = ProgressData.from_key(progress_key)
    update_sub_progress_total(100, sub_progress_key)

    # Don't query the org table here, just get the organization from the import_record
    org = import_file.import_record.super_organization

    # Set the progress to started - 33%
    progress_data.step("Matching data")

    # Set defaults
    # property - within file
    property_initial_incoming_count = 0
    property_duplicates_within_file_count = 0
    property_duplicates_within_file_errors = []
    property_merges_within_file_count = 0
    property_merges_within_file_errors = []

    # property - within existing records
    property_merges_between_existing_count = 0

    # property - introduce file to existing
    property_duplicates_against_existing_count = 0
    merged_property_views = []
    merged_property_state_errors = []
    linked_property_views = []
    linked_property_state_errors = []
    new_property_views = []
    new_property_state_errors = []

    # taxlot - within  file
    tax_lot_initial_incoming_count = 0
    tax_lot_duplicates_within_file_count = 0
    tax_lot_duplicates_within_file_errors = []
    tax_lot_merges_within_file_count = 0
    tax_lot_merges_within_file_errors = []

    # taxlot - within existing records
    taxlot_merges_between_existing_count = 0

    # taxlot - introduce file to existing
    taxlot_duplicates_against_existing_count = 0
    merged_taxlot_views = []
    merged_taxlot_state_errors = []
    linked_taxlot_views = []
    linked_taxlot_state_errors = []
    new_taxlot_views = []
    new_taxlot_state_errors = []

    # Get lists and counts of all the properties and tax lots based on the import file.
    property_initial_incoming_count = incoming_properties.count()
    tax_lot_initial_incoming_count = incoming_tax_lots.count()

    if property_initial_incoming_count > 0:
        # If importing BuildingSync, we will not just skip duplicates like we normally
        # do. Since we don't skip them, they will eventually get merged into their "duplicate".
        # We do this b/c though the property data might be the same, the Scenarios, Measures,
        # or Meters might have been updated. The merging flow is able to "transfer"
        # this data, while skipping duplicates cannot.
        merge_duplicates = import_file.from_buildingsync

        # Matching step 1/6 for properties
        # Within the ImportFile, filter out the duplicates.
        log_debug("Start Properties filter_duplicate_states")
        if merge_duplicates:
            promoted_property_ids, property_duplicates_within_file_count = incoming_properties.values_list("id", flat=True), 0
        else:
            promoted_property_ids, property_duplicates_within_file_errors, property_duplicates_within_file_count = filter_duplicate_states(
                incoming_properties,
                sub_progress_key,
            )

        # Matching step 2/6 for properties
        # Within the ImportFile, merge -States together based on user defined matching_criteria
        log_debug("Start Properties inclusive_match_and_merge")
        promoted_property_ids, property_merges_within_file_count, property_merges_within_file_errors = inclusive_match_and_merge(
            promoted_property_ids,
            org,
            PropertyState,
            sub_progress_key,
        )

        # Matching steps 3-5/6 for properties
        # Filter Cycle-wide duplicates then merge and/or assign -States to -Views
        log_debug("Start Properties states_to_views")
        (
            property_merges_between_existing_count,
            property_duplicates_against_existing_count,
            merged_property_views,
            merged_property_state_errors,  # TODO: we don't do anything with these. they should probably be deleted.
            new_property_views,
            errored_new_property_states,
        ) = states_to_views(
            promoted_property_ids,
            org,
            import_file.import_record.access_level_instance,
            cycle,
            PropertyState,
            sub_progress_key,
            merge_duplicates,
        )

        # Matching step 6/6 for properties
        # Look for links across Cycles
        log_debug("Start Properties link_views")
        (
            merged_property_views,
            # no merged_property_state_errors, they got off the ride before linking
            linked_property_views,  # note: view that merge _and_ linked are in merged_property_views, not linked_property_views
            linked_property_state_errors,
            new_property_views,
            new_property_state_errors,
        ) = link_views_and_states(
            merged_property_views,
            new_property_views,
            errored_new_property_states,
            PropertyView,
            cycle,
            import_file.import_record.access_level_instance,
            sub_progress_key,
        )

        # TODO: the states and Property should probably be deleted too
        PropertyView.objects.filter(state__in=linked_property_state_errors).delete()

    if tax_lot_initial_incoming_count > 0:
        # Matching step 1/6 for taxlots
        # Within the ImportFile, filter out the duplicates.
        log_debug("Start TaxLots filter_duplicate_states")
        promoted_tax_lot_ids, tax_lot_duplicates_within_file_errors, tax_lot_duplicates_within_file_count = filter_duplicate_states(
            incoming_tax_lots,
            sub_progress_key,
        )

        # Matching step 2/6 for taxlots
        # Within the ImportFile, merge -States together based on user defined matching_criteria
        log_debug("Start TaxLots inclusive_match_and_merge")
        promoted_tax_lot_ids, tax_lot_merges_within_file_count, tax_lot_merges_within_file_errors = inclusive_match_and_merge(
            promoted_tax_lot_ids,
            org,
            TaxLotState,
            sub_progress_key,
        )

        # Matching steps 3-5/6 for taxlots
        # Filter Cycle-wide duplicates then merge and/or assign -States to -Views
        log_debug("Start TaxLots states_to_views")
        (
            taxlot_merges_between_existing_count,
            taxlot_duplicates_against_existing_count,
            merged_taxlot_views,
            merged_taxlot_state_errors,  # TODO: we don't do anything with these. they should probably be deleted.
            new_taxlot_views,
            errored_new_taxlot_states,
        ) = states_to_views(
            promoted_tax_lot_ids,
            org,
            import_file.import_record.access_level_instance,
            cycle,
            TaxLotState,
            sub_progress_key,
        )

        # Matching step 6/6 for taxlots
        # Look for links across Cycles
        log_debug("Start TaxLots link_views")
        (
            merged_taxlot_views,
            # no merged_taxlot_state_errors, they got off the ride before linking
            linked_taxlot_views,  # note: view that merge _and_ linked are in merged_taxlot_views, not linked_taxlot_views
            linked_taxlot_state_errors,
            new_taxlot_views,
            new_taxlot_state_errors,
        ) = link_views_and_states(
            merged_taxlot_views,
            new_taxlot_views,
            errored_new_taxlot_states,
            TaxLotView,
            cycle,
            import_file.import_record.access_level_instance,
            sub_progress_key,
        )

        # TODO: the states and taxlot should probably be deleted too
        errored_linked_taxlot_views = TaxLotView.objects.filter(state__in=linked_taxlot_state_errors)
        errored_linked_taxlot_views.delete()

    log_debug("Start pair_new_states")
    progress_data.step("Pairing data")
    pair_new_states(
        linked_property_views + new_property_views + merged_property_views,
        linked_taxlot_views + new_taxlot_views + merged_taxlot_views,
        sub_progress_key,
    )

    from seed.models import Column, DerivedColumn
    from seed.tasks import update_state_derived_data

    derived_columns = DerivedColumn.objects.filter(organization_id=org.id)
    Column.objects.filter(derived_column__in=derived_columns).update(is_updating=True)
    derived_column_ids = list(derived_columns.values_list("id", flat=True))
    update_state_derived_data(
        property_state_ids=[v.state_id for v in new_property_views + merged_property_views],
        taxlot_state_ids=[v.state_id for v in new_taxlot_views + merged_taxlot_views],
        derived_column_ids=derived_column_ids,
    )

    return {
        # property - within file
        "property_initial_incoming": property_initial_incoming_count,
        "property_duplicates_within_file": property_duplicates_within_file_count,
        "property_duplicates_within_file_errors": len(property_duplicates_within_file_errors),
        "property_merges_within_file": property_merges_within_file_count,
        "property_merges_within_file_errors": len(property_merges_within_file_errors),
        # property - within existing records
        "property_merges_between_existing": property_merges_between_existing_count,
        # property - introduce file to existing
        "property_duplicates_against_existing": property_duplicates_against_existing_count,
        "property_merges_against_existing": len(merged_property_views),
        "property_merges_against_existing_errors": len(merged_property_state_errors),
        "property_links_against_existing": len(linked_property_views),
        "property_links_against_existing_errors": len(linked_property_state_errors),
        "property_new": len(new_property_views),
        "property_new_errors": len(new_property_state_errors),
        # taxlot - within  file
        "tax_lot_initial_incoming": tax_lot_initial_incoming_count,
        "tax_lot_duplicates_within_file": tax_lot_duplicates_within_file_count,
        "tax_lot_duplicates_within_file_errors": len(tax_lot_duplicates_within_file_errors),
        "tax_lot_merges_within_file": tax_lot_merges_within_file_count,
        "tax_lot_merges_within_file_errors": len(tax_lot_merges_within_file_errors),
        # taxlot - within existing records
        "tax_lot_merges_between_existing": taxlot_merges_between_existing_count,
        # taxlot - introduce file to existing
        "tax_lot_duplicates_against_existing": taxlot_duplicates_against_existing_count,
        "tax_lot_merges_against_existing": len(merged_taxlot_views),
        "tax_lot_merges_against_existing_errors": len(merged_taxlot_state_errors),
        "tax_lot_links_against_existing": len(linked_taxlot_views),
        "tax_lot_links_against_existing_errors": len(linked_taxlot_state_errors),
        "tax_lot_new": len(new_taxlot_views),
        "tax_lot_new_errored": len(new_taxlot_state_errors),
    }


def link_views_and_states(merged_views, new_views, errored_new_states, ViewClass, cycle, ali, sub_progress_key):  # noqa: N803
    state_class_name = "PropertyState" if ViewClass == PropertyView else "TaxLotState"
    class_name = "property" if ViewClass == PropertyView else "taxlot"

    # these are our matching columns
    matching_columns = get_matching_criteria_column_names(cycle.organization_id, state_class_name)
    check_jaccard = "ubid" in matching_columns
    tuple_values = matching_columns.copy()
    tuple_values.discard("ubid")

    # This is ALL the org's views that ARE NOT in the give cycle, by their matching column values
    existing_views = (
        ViewClass.objects.select_related("state").filter(**{f"{class_name}__organization_id": cycle.organization_id}).exclude(cycle=cycle)
    )
    view_lookup: dict[int, Union[PropertyState, TaxLotState]] = {view.state.id: view for view in existing_views}
    match_lookup: dict[tuple, list[dict[str, any]]] = defaultdict(list)
    for state in ({k: getattr(view.state, k) for k in ["id", "hash_object", "updated", *matching_columns]} for view in existing_views):
        match_lookup[tuple(state[c] for c in tuple_values)].append(state)

    shared_args = [ViewClass, cycle, ali, sub_progress_key, tuple_values, view_lookup, match_lookup, check_jaccard]

    # merged_property_views are attached to properties that existed in the db prior to import, so it
    # REALLY should not fail.
    (
        merged_and_linked_views,
        merged_views,
        _merge_and_linked_states_errors,
        _,
    ) = link_states([v.state for v in merged_views], *shared_args)

    # new_views may try to link invalidly if the existing records has a different ali. In that case,
    # the new record should have never been created.
    (
        linked_views_a,
        new_views,
        linked_state_errors_a,
        _,
    ) = link_states([v.state for v in new_views], *shared_args)

    # errored_new_states are new states without alis that also didn't merge. If they don't link or
    # try to link invalidly, we throw them out. As there are not yet attached to a record, successfully
    # not linking is not an option.
    (
        linked_views_b,
        _,
        linked_state_errors_b,
        new_state_errors,
    ) = link_states(errored_new_states, *shared_args)

    merged_views += merged_and_linked_views
    linked_views = linked_views_a + linked_views_b
    linked_state_errors = linked_state_errors_a + linked_state_errors_b

    return merged_views, linked_views, linked_state_errors, new_views, new_state_errors


def filter_duplicate_states(unmatched_states, sub_progress_key):
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
    :return: canonical_state_ids, errors_state_ids, duplicate_count
    """
    sub_progress_data = update_sub_progress_total(4, sub_progress_key)
    sub_progress_data.step("Matching Data (1/6): Filtering Duplicate States")

    states_grouped_by_hash = unmatched_states.values("hash_object").annotate(
        duplicate_sets=ArrayAgg("id"), duplicate_sets_ali=ArrayAgg("raw_access_level_instance_id")
    )

    sub_progress_data.step("Matching Data (1/6): Filtering Duplicate States")

    # For group of states with the same ali, find and select the canonical_state
    # For consistency, take the first member of each of the duplicate sets
    canonical_state_ids = []
    duplicate_state_ids = []
    errors_state_ids = []
    for states in states_grouped_by_hash:
        state_ids = [{"id": id, "ali_id": ali_id} for id, ali_id in zip(states["duplicate_sets"], states["duplicate_sets_ali"])]
        state_ids.sort(key=lambda x: x["id"])
        states_with_ali = [s for s in state_ids if s["ali_id"] is not None]
        present_ali_ids = {s["ali_id"] for s in states_with_ali}

        # None have alis, just choose first
        if len(present_ali_ids) == 0:
            canonical_state = state_ids[0]

        # One ali! choose the first non-null
        elif len(present_ali_ids) == 1:
            canonical_state = states_with_ali[0]

        # More than one ali was specified! all of these duplicates are invalid
        else:
            errors_state_ids.extend(s["id"] for s in state_ids)
            continue

        canonical_state_ids.append(canonical_state["id"])
        state_ids.remove(canonical_state)
        duplicate_state_ids.extend(s["id"] for s in state_ids)

    sub_progress_data.step("Matching Data (1/6): Filtering Duplicate States")
    duplicate_count = unmatched_states.filter(pk__in=duplicate_state_ids).update(data_state=DATA_STATE_DELETE)

    sub_progress_data.step("Matching Data (1/6): Filtering Duplicate States")
    sub_progress_data.finish_with_success()
    return canonical_state_ids, errors_state_ids, duplicate_count


def inclusive_match_and_merge(unmatched_state_ids, org, StateClass, sub_progress_key):  # noqa: N803
    """
    Takes a list of unmatched_state_ids, combines matches of the corresponding
    -States, and returns a set of IDs of the remaining -States.

    :param unmatched_state_ids: list
    :param org: Organization object
    :param StateClass: PropertyState or TaxLotState
    :return: promoted_ids: list
    """
    column_names = get_matching_criteria_column_names(org.id, StateClass.__name__)

    sub_progress_data = update_sub_progress_total(100, sub_progress_key)

    # IDs of -States with all matching criteria equal to None are initially promoted
    # as they're not eligible for matching.
    promoted_ids = list(
        StateClass.objects.filter(pk__in=unmatched_state_ids, **empty_criteria_filter(StateClass, column_names)).values_list(
            "id", flat=True
        )
    )

    # Update the list of IDs whose states haven't been checked for matches.
    unmatched_state_ids = list(set(unmatched_state_ids) - set(promoted_ids))
    # Group IDs by -States that match each other
    matched_id_groups = (
        StateClass.objects.filter(id__in=unmatched_state_ids)
        .values(*column_names)
        .annotate(matched_ids=ArrayAgg("id"))
        .values_list("matched_ids", flat=True)
    )

    # Collapse groups of matches found in the previous step into 1 -State per group
    merges_within_file = 0
    errored_states = []
    priorities = Column.retrieve_priorities(org)
    batch_size = math.ceil(len(matched_id_groups) / 100)
    for idx, ids in enumerate(matched_id_groups):
        if len(ids) == 1:
            # If there's only 1, no merging is needed, so just promote the ID.
            promoted_ids += ids
        else:
            states = list(StateClass.objects.filter(pk__in=ids).order_by("-id"))
            raw_ali_ids = {s.raw_access_level_instance for s in states if s.raw_access_level_instance is not None}
            if len(raw_ali_ids) > 1:
                errored_states += states
                continue

            merge_state = states.pop()

            merges_within_file += len(states)

            while len(states) > 0:
                newer_state = states.pop()
                merge_state = save_state_match(merge_state, newer_state, priorities)

            promoted_ids.append(merge_state.id)
        if batch_size > 0 and idx % batch_size == 0:
            sub_progress_data.step("Matching Data (2/6): Inclusive Matching and Merging")

    sub_progress_data.finish_with_success()

    # Flag the soon-to-be promoted ID -States as having gone through matching
    StateClass.objects.filter(pk__in=promoted_ids).update(data_state=DATA_STATE_MATCHING)

    return promoted_ids, merges_within_file, errored_states


def states_to_views(unmatched_state_ids, org, access_level_instance, cycle, StateClass, sub_progress_key, merge_duplicates=False):  # noqa: N803
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

    :param unmatched_state_ids: list
    :param org: Organization object
    :param access_level_instance
    :param cycle: Cycle object
    :param StateClass: PropertyState or TaxLotState
    :param sub_progress_key
    :param merge_duplicates: bool, if True, we keep the duplicates and merge them
        instead of skipping them. This is used when importing BuildingSync files.
    :return: processed_views, duplicate_count, new + matched counts
    """
    table_name = StateClass.__name__

    sub_progress_data = update_sub_progress_total(100, sub_progress_key)

    unmatched_state_ids = set(unmatched_state_ids)

    if table_name == "PropertyState":
        ViewClass = PropertyView
    elif table_name == "TaxLotState":
        ViewClass = TaxLotView

    matching_columns = get_matching_criteria_column_names(org.id, table_name)
    # compare UBIDs via jaccard index instead of a direct match
    check_jaccard = "ubid" in matching_columns

    # Fetch existing states tied to views, and create a tuple-lookup using non-UBID matching columns
    tuple_values = matching_columns.copy()
    tuple_values.discard("ubid")
    existing_views = ViewClass.objects.select_related("state").filter(cycle_id=cycle)
    state_lookup: dict[int, Union[PropertyState, TaxLotState]] = {view.state.id: view.state for view in existing_views}
    match_lookup: dict[tuple, list[dict[str, any]]] = defaultdict(list)
    for state in ({k: getattr(view.state, k) for k in ["id", "hash_object", "updated", *matching_columns]} for view in existing_views):
        match_lookup[tuple(state[c] for c in tuple_values)].append(state)

    if merge_duplicates:
        duplicate_state_ids = set()
        duplicate_count = 0
    else:
        # Apply DATA_STATE_DELETE to incoming duplicate -States of existing -States in Cycle
        duplicate_states = StateClass.objects.filter(
            pk__in=unmatched_state_ids, hash_object__in=Subquery(existing_views.values("state__hash_object"))
        ).only("id")
        duplicate_state_ids = set(duplicate_states.values_list("id", flat=True))
        duplicate_count = duplicate_states.update(data_state=DATA_STATE_DELETE)

    # For the remaining incoming -States (filtering those duplicates), identify
    # -States with all matching criteria being None. These aren't eligible for matching.
    empty_matching_criteria = empty_criteria_filter(StateClass, matching_columns)
    promote_state_ids = set(
        StateClass.objects.filter(pk__in=unmatched_state_ids.difference(duplicate_state_ids), **empty_matching_criteria).values_list(
            "id", flat=True
        )
    )

    # Identify and filter out -States that have been "handled".
    handled_state_ids = promote_state_ids.union(duplicate_state_ids)
    unmatched_states = StateClass.objects.filter(pk__in=unmatched_state_ids.difference(handled_state_ids))

    # For the remaining -States, search for a match within the -States that are attached to -Views.
    # If one match is found, pass that along.
    # If multiple matches are found, merge them together, pass along the resulting record.
    # Otherwise, add current -State to be promoted as-is.
    merged_between_existing_count = 0
    merge_state_pairs: list[Union[tuple[PropertyState, PropertyState], tuple[TaxLotState, TaxLotState]]] = []
    batch_size = math.ceil(len(unmatched_states) / 100)

    for idx, state in enumerate(unmatched_states):
        matching_criteria = matching_filter_criteria(state, matching_columns)
        existing_state_matches = match_lookup.get(tuple(getattr(state, c) for c in tuple_values), [])

        if check_jaccard:
            existing_state_matches = [
                existing_state
                for existing_state in existing_state_matches
                if check_jaccard_match(matching_criteria.get("ubid"), existing_state.get("ubid"), org.ubid_threshold)
            ]

        count = len(existing_state_matches)

        if count > 1:
            merged_between_existing_count += count
            existing_state_ids = [state["id"] for state in sorted(existing_state_matches, key=lambda state: state["updated"])]
            # The following merge action ignores merge protection and prioritizes -States by most recent AuditLog
            merged_state = merge_states_with_views(existing_state_ids, org.id, "System Match", StateClass)
            merge_state_pairs.append((merged_state, state))
        elif count == 1:
            merge_state_pairs.append((state_lookup[existing_state_matches[0]["id"]], state))
        else:
            promote_state_ids.add(state.id)

        if batch_size > 0 and idx % batch_size == 0:
            sub_progress_data.step("Matching Data (3/6): Merging Unmatched States")

    sub_progress_data = update_sub_progress_total(100, sub_progress_key, finish=True)

    # Process -States into -Views either directly (promoted_ids) or post-merge (merge_state_pairs).
    _log.debug(f"There are {len(merge_state_pairs)} merge_state_pairs and {len(promote_state_ids)} promote_states")
    priorities = Column.retrieve_priorities(org.pk)
    try:
        with transaction.atomic():
            # For each merge_state_pairs, try to merge the new state into the existing property views
            merged_views = []
            merged_state_ids = []
            errored_merged_states = []
            batch_size = math.ceil(len(merge_state_pairs) / 100)

            # Create a lookup of state id to view
            canonical_field = "property" if table_name == "PropertyState" else "taxlot"
            view_lookup = {
                view.state_id: view
                for view in ViewClass.objects.select_related(f"{canonical_field}__access_level_instance").filter(
                    state_id__in=[existing_state.id for existing_state, _ in merge_state_pairs]
                )
            }

            for idx, state_pair in enumerate(merge_state_pairs):
                existing_state, newer_state = state_pair
                existing_view = view_lookup.get(existing_state.id)
                if not existing_view:
                    continue
                ali = getattr(existing_view, canonical_field).access_level_instance

                # ensure that new ali and existing ali match and that we have access to existing ali.
                new_ali = newer_state.raw_access_level_instance
                if new_ali is None:
                    if not (ali == access_level_instance or ali.is_descendant_of(access_level_instance)):
                        errored_merged_states.append(newer_state)
                        continue
                elif ali != new_ali:
                    errored_merged_states.append(newer_state)
                    continue

                # Merge -States and assign new/merged -State to existing -View
                merged_state = save_state_match(existing_state, newer_state, priorities)
                merge_ubid_models([existing_state.id, newer_state.id], merged_state.id, StateClass)
                existing_view.state = merged_state
                existing_view.save()

                merged_views.append(existing_view)
                merged_state_ids.append(merged_state.id)
                if batch_size > 0 and idx % batch_size == 0:
                    sub_progress_data.step("Matching Data (4/6): Merging State Pairs")

            sub_progress_data = update_sub_progress_total(100, sub_progress_key, finish=True)

            # For each state that doesn't merge into an existing property, promote it, creating a new property
            new_views = []
            promoted_state_ids = []
            errored_new_states = []
            if len(promote_state_ids) > 0:
                batch_size = math.ceil(len(promote_state_ids) / 100)
                promote_states = StateClass.objects.filter(pk__in=promote_state_ids)
                for idx, state in enumerate(promote_states):
                    created_view = state.promote(cycle)
                    if created_view is None:
                        errored_new_states.append(state)
                    else:
                        promoted_state_ids.append(state.id)
                        new_views.append(created_view)
                    if batch_size > 0 and idx % batch_size == 0:
                        sub_progress_data.step("Matching Data (5/6): Promoting States")
            sub_progress_data.finish_with_success()

    except IntegrityError as e:
        raise IntegrityError("Could not merge results with error: %s" % (e))

    # update merge_state while excluding any states that were a product of a previous, file-inclusive merge
    StateClass.objects.filter(pk__in=promoted_state_ids).exclude(merge_state=MERGE_STATE_MERGED).update(merge_state=MERGE_STATE_NEW)
    StateClass.objects.filter(pk__in=merged_state_ids).update(data_state=DATA_STATE_MATCHING, merge_state=MERGE_STATE_MERGED)

    return (
        merged_between_existing_count,
        duplicate_count,
        list(set(merged_views)),  # so no dupes, I think?
        errored_merged_states,
        new_views,
        errored_new_states,
    )


def link_states(states, ViewClass, cycle, highest_ali, sub_progress_key, tuple_values, view_lookup, match_lookup, check_jaccard):  # noqa: N803    
    class_name = "property" if ViewClass == PropertyView else "taxlot"

    # set up the progress bar
    sub_progress_data = update_sub_progress_total(100, sub_progress_key)
    batch_size = math.ceil(len(states) / 100)

    linked_views = []
    unlinked_views = []
    invalid_link_states = []
    unlinked_states = []
    for idx, state in enumerate(states):
        # get matches
        existing_state_matches = match_lookup.get(tuple(getattr(state, c) for c in tuple_values), [])
        if check_jaccard:
            existing_state_matches = [
                existing_state
                for existing_state in existing_state_matches
                if check_jaccard_match(state.ubid, existing_state.get("ubid"), cycle.organization.ubid_threshold)
            ]
        existing_views_matches = [view_lookup[x["id"]] for x in existing_state_matches]

        # ensure ali is correct
        view = ViewClass.objects.filter(state_id=state.id, cycle_id=cycle.id).select_related(f"{class_name}__access_level_instance").first()
        try:
            ali = _get_ali(view, existing_views_matches, highest_ali, class_name)
        except (MultipleALIError, NoAccessError):
            invalid_link_states.append(state.id)
            continue
        except NoViewsError:
            unlinked_states.append(state.id)
            continue

        # if a view for this cycle doesn't already exist, create one
        if view is None:
            state.raw_access_level_instance = ali
            view = state.promote(cycle=cycle)

        # Add labels RP
        if view and state.incoming_property_labels:
            incoming_label_names = state.incoming_property_labels
            incoming_label_names = incoming_label_names.split(',')
            for incoming_label_name in incoming_label_names:
                incoming_label, _ = StatusLabel.objects.get_or_create(name=incoming_label_name, super_organization=cycle.organization)
                PropertyViewLabel.objects.get_or_create(statuslabel=incoming_label, propertyview=view)


        # link state
        link_count = _link_matches([*existing_views_matches, view], cycle.organization_id, view, ViewClass)
        if link_count == 0:
            unlinked_views.append(view)
        else:
            linked_views.append(view)

        if batch_size > 0 and idx % batch_size == 0:
            sub_progress_data.step("Matching Data (6/6): Merging Views")

    sub_progress_data.finish_with_success()

    return linked_views, unlinked_views, invalid_link_states, unlinked_states


def save_state_match(state1, state2, priorities):
    """
    Merge the contents of state2 into state1

    :param state1: PropertyState or TaxLotState
    :param state2: PropertyState or TaxLotState
    :param priorities: dict, column names and the priorities of the merging of data. This includes
    all of the priorities for the columns, not just the priorities for the selected taxlotstate.
    :return: state1, after merge
    """
    merged_state = type(state1).objects.create(organization=state1.organization)

    merged_state = merging.merge_state(merged_state, state1, state2, priorities[merged_state.__class__.__name__])

    AuditLogClass = PropertyAuditLog if isinstance(merged_state, PropertyState) else TaxLotAuditLog

    if AuditLogClass.objects.filter(state=state1).count() == 0:
        # If there is no audit log for state1, then there is an error!
        # get the info of the object that is causing the issue
        raise Exception(f"No audit log for merging of (base) state. Base {state1.id}, Incoming {state2.id}")

    if AuditLogClass.objects.filter(state=state2).count() == 0:
        # If there is no audit log for state1, then there is an error!
        # get the info of the object that is causing the issue
        raise Exception(f"No audit log for merging of (incoming) state. Base {state1.id}, Incoming {state2.id}")

    # NJACHECK - is this logic correct?
    state_1_audit_log = AuditLogClass.objects.filter(state=state1).first()
    state_2_audit_log = AuditLogClass.objects.filter(state=state2).first()

    AuditLogClass.objects.create(
        organization=state1.organization,
        parent1=state_1_audit_log,
        parent2=state_2_audit_log,
        parent_state1=state1,
        parent_state2=state2,
        state=merged_state,
        name="System Match",
        description="Automatic Merge",
        import_filename=None,
        record_type=AUDIT_IMPORT,
    )

    # If the two states being merged were just imported from the same import file, carry the import_file_id into the new
    # state. Also merge the lot_number fields so that pairing can work correctly on the resulting merged record
    # Possible conditions:
    # state1.data_state = 2, state1.merge_state = 0 and state2.data_state = 2, state2.merge_state = 0
    # state1.data_state = 0, state1.merge_state = 2 and state2.data_state = 2, state2.merge_state = 0
    if state1.import_file_id == state2.import_file_id and (
        (
            state1.data_state == DATA_STATE_MAPPING
            and state1.merge_state == MERGE_STATE_UNKNOWN
            and state2.data_state == DATA_STATE_MAPPING
            and state2.merge_state == MERGE_STATE_UNKNOWN
        )
        or (
            state1.data_state == DATA_STATE_UNKNOWN
            and state1.merge_state == MERGE_STATE_MERGED
            and state2.data_state == DATA_STATE_MAPPING
            and state2.merge_state == MERGE_STATE_UNKNOWN
        )
    ):
        merged_state.import_file_id = state1.import_file_id

        if isinstance(merged_state, PropertyState):
            joined_lots = set()
            if state1.lot_number:
                joined_lots = joined_lots.union(state1.lot_number.split(";"))
            if state2.lot_number:
                joined_lots = joined_lots.union(state2.lot_number.split(";"))
            if joined_lots:
                merged_state.lot_number = ";".join(joined_lots)

    # Set the merged_state to merged
    merged_state.merge_state = MERGE_STATE_MERGED
    merged_state.save()

    return merged_state


def check_jaccard_match(ubid: str, state_ubid: str, ubid_threshold: float):
    """
    Use jaccard index between an incoming ubid and an existing state_ubid to determine if states are 'matching'
    If one ubid is None, 0.0 will be returned.

    :param ubid: string, incoming ubid
    :param state_ubid: string, existing state's ubid
    :param ubid_threshold: float, organization's ubid_threshold
    """
    jaccard_index = get_jaccard_index(ubid, state_ubid)

    if ubid_threshold == 0:
        return jaccard_index > ubid_threshold
    else:
        return jaccard_index >= ubid_threshold
