# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""
import logging
from collections import defaultdict

from seed.models import (
    Column,
    PropertyState,
    TaxLotState,
)

_log = logging.getLogger(__name__)


def get_attrs_with_mapping(data_set_buildings, mapping):
    """
    Returns a dictionary of attributes from each data_set_building.

    :param data_set_buildings: list, instances to merge.
    :param mapping:
    :return: dict: possible attributes keyed on attr name.

    .. code-block::python

        {
            'property_name': {
                building_inst1: 'value', building_inst2: 'value2'
            }
        }

    """

    can_attrs = defaultdict(dict)
    for data_set_building in data_set_buildings:
        for data_set_attr, can_attr in mapping:
            # Catch import_file because getattr will not return the ID of the object, rather, the
            # foreign object is returned. If the import_file has been deleted (or at least the
            # deleted flag is set), then this would crash because the query does not return an
            # object.
            if can_attr == 'import_file':
                data_set_value = data_set_building.import_file_id
                can_attrs['import_file_id'][data_set_building] = data_set_value
            else:
                data_set_value = getattr(data_set_building, data_set_attr)
                can_attrs[can_attr][data_set_building] = data_set_value

    return can_attrs


def get_state_to_state_tuple(inventory):
    """Return the list of the database fields based on the inventory type"""
    columns = Column.retrieve_db_fields_from_db_tables()

    fields = []
    for c in columns:
        if c['table_name'] == inventory:
            fields.append(c['column_name'])

    # Include geocoding results columns that are left out when generating duplicate hashes
    fields.append('long_lat')
    fields.append('geocoding_confidence')

    return tuple([(k, k) for k in sorted(fields)])


def get_propertystate_attrs(data_set_buildings):
    state_to_state = get_state_to_state_tuple('PropertyState')
    return get_attrs_with_mapping(data_set_buildings, state_to_state)


def get_taxlotstate_attrs(data_set_buildings):
    state_to_state = get_state_to_state_tuple('TaxLotState')
    return get_attrs_with_mapping(data_set_buildings, state_to_state)


def get_state_attrs(state_list):
    """Return a list of state attributes. This does not include any of the extra data columns"""
    if not state_list:
        return []

    if isinstance(state_list[0], PropertyState):
        return get_propertystate_attrs(state_list)
    elif isinstance(state_list[0], TaxLotState):
        return get_taxlotstate_attrs(state_list)


def _merge_geocoding_results(merged_state, state1, state2, priorities, can_attrs, ignore_merge_protection=False):
    """
    Geocoding results need to be handled separately since they should generally
    "stick together". In one sense, all 4 result columns should be treated as
    one column. Specifically, the complete geocoding results of either the new
    state or the existing state is used - not a combination of the geocoding
    results from each.

    Note, to avoid unnecessary complications, it's intended for these fields to
    be left out of the logic involving recognize_empty.
    """
    geocoding_attr_cols = [
        'geocoding_confidence',
        'longitude',
        'latitude',
        'long_lat',  # note this col shouldn't have priority set
    ]

    existing_results_empty = True
    new_results_empty = True
    geocoding_favor_new = True

    for geocoding_col in geocoding_attr_cols:
        existing_results_empty = existing_results_empty and can_attrs[geocoding_col][state1] is None
        new_results_empty = new_results_empty and can_attrs[geocoding_col][state2] is None

        geocoding_favor_new = geocoding_favor_new and priorities.get(geocoding_col, 'Favor New') == 'Favor New'

        # Since these are handled here, remove them from canonical attributes
        del can_attrs[geocoding_col]

    # Multiple elif's here is necessary since empty checks should be first, followed by merge protection settings
    if new_results_empty:
        geo_state = state1
    elif existing_results_empty:
        geo_state = state2
    elif ignore_merge_protection:
        geo_state = state2
    elif geocoding_favor_new:
        geo_state = state2
    else:   # favor existing
        geo_state = state1

    for geo_attr in geocoding_attr_cols:
        setattr(merged_state, geo_attr, getattr(geo_state, geo_attr, None))


def _merge_extra_data(ed1, ed2, priorities, recognize_empty_columns, ignore_merge_protection=False):
    """
    Merge extra_data field between two extra data dictionaries, return result.

    :param ed1: dict, left extra data
    :param ed2: dict, right extra data
    :param priorities: dict, column names with favor new or existing
    :return dict, merged result
    """
    all_keys = set(list(ed1.keys()) + list(ed2.keys()))
    extra_data = {}
    for key in all_keys:
        recognize_empty = key in recognize_empty_columns
        val1 = ed1.get(key, None)
        val2 = ed2.get(key, None)
        if (val1 and val2) or recognize_empty:
            # decide based on the priority which one to use
            col_prior = priorities.get(key, 'Favor New')
            if ignore_merge_protection or col_prior == 'Favor New':
                extra_data[key] = val2
            else:  # favor the existing field
                extra_data[key] = val1
        else:
            extra_data[key] = val1 or val2

    return extra_data


def merge_state(merged_state, state1, state2, priorities, ignore_merge_protection=False):
    """
    Set attributes on our Canonical model, saving differences.

    :param merged_state: PropertyState/TaxLotState model inst.
    :param state1: PropertyState/TaxLotState model inst. Left parent.
    :param state2: PropertyState/TaxLotState model inst. Right parent.
    :param priorities: dict, column names with favor new or existing
    :return: inst(``merged_state``), updated.
    """
    # Calculate the difference between the two states and save into a dictionary
    can_attrs = get_state_attrs([state1, state2])

    # Handle geocoding results first so that recognize_empty logic is not processed on them.
    _merge_geocoding_results(merged_state, state1, state2, priorities, can_attrs, ignore_merge_protection)

    recognize_empty_columns = state2.organization.column_set.filter(
        table_name=state2.__class__.__name__,
        recognize_empty=True,
        is_extra_data=False
    ).values_list('column_name', flat=True)

    default = state2
    for attr in can_attrs:
        recognize_empty = attr in recognize_empty_columns

        attr_values = [
            value
            for value
            in list(can_attrs[attr].values())
            if value is not None or recognize_empty
        ]

        attr_value = None
        # Two, differing values are set.
        if len(attr_values) > 1:
            # If we have more than one value for this field, choose based on the column priority
            col_prior = priorities.get(attr, 'Favor New')
            if ignore_merge_protection or col_prior == 'Favor New':
                attr_value = can_attrs[attr][state2]
            else:  # favor the existing field
                attr_value = can_attrs[attr][state1]

        # No values are set
        elif len(attr_values) < 1:
            attr_value = None

        # There is only one value set.
        else:
            attr_value = attr_values.pop()

        if callable(attr):
            # This callable will be responsible for setting the attribute value, not just returning it.
            attr(merged_state, default)
        else:
            setattr(merged_state, attr, attr_value)

    recognize_empty_ed_columns = state2.organization.column_set.filter(
        table_name=state2.__class__.__name__,
        recognize_empty=True,
        is_extra_data=True
    ).values_list('column_name', flat=True)

    merged_state.extra_data = _merge_extra_data(
        state1.extra_data,
        state2.extra_data,
        priorities['extra_data'],
        recognize_empty_ed_columns,
        ignore_merge_protection
    )

    # merge measures, scenarios, simulations
    if isinstance(merged_state, PropertyState):
        PropertyState.merge_relationships(merged_state, state1, state2)

    return merged_state
