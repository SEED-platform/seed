# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
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


def _merge_extra_data(ed1, ed2, priorities):
    """
    Merge extra_data field between two extra data dictionaries, return result.

    :param ed1: dict, left extra data
    :param ed2: dict, right extra data
    :param priorities: dict, column names with favor new or existing
    :return dict, merged result
    """
    all_keys = set(ed1.keys() + ed2.keys())
    extra_data = {}
    for key in all_keys:
        val1 = ed1.get(key, None)
        val2 = ed2.get(key, None)
        if val1 and val2:
            # decide based on the priority which one to use
            col_prior = priorities.get(key, 'Favor New')
            if col_prior == 'Favor New':
                extra_data[key] = val2
            else:  # favor the existing field
                extra_data[key] = val1
        else:
            extra_data[key] = val1 or val2

    return extra_data


def merge_state(merged_state, state1, state2, priorities):
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

    default = state2
    for attr in can_attrs:
        # Do we have any differences between these fields? - Check if not None instead of if value.
        attr_values = list(set([value for value in can_attrs[attr].values() if value is not None]))
        attr_values = [v for v in attr_values if v is not None]

        attr_value = None
        # Two, differing values are set.
        if len(attr_values) > 1:
            # If we have more than one value for this field, choose based on the column priority
            col_prior = priorities.get(attr, 'Favor New')
            if col_prior == 'Favor New':
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

    merged_state.extra_data = _merge_extra_data(state1.extra_data, state2.extra_data, priorities['extra_data'])

    # merge measures, scenarios, simulations
    if isinstance(merged_state, PropertyState):
        PropertyState.merge_relationships(merged_state, state1, state2)

    return merged_state
