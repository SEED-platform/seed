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


def _merge_extra_data(b1, b2, default=None):
    """Merge extra_data field between two BuildingSnapshots, return result.

    :param b1: BuildingSnapshot inst.
    :param b2: BuildingSnapshot inst.
    :param default: BuildingSnapshot inst.
    :returns tuple of dict:

    .. code-block::python

        # first dict contains values, second the source pks.
        ({'data': 'value'}, {'data': 23},)

    """
    default = default or b1
    non_default = b2
    if default != b1:
        non_default = b1

    extra_data_sources = {}
    default_extra_data = getattr(default, 'extra_data', {})
    non_default_extra_data = getattr(non_default, 'extra_data', {})

    all_keys = set(default_extra_data.keys() + non_default_extra_data.keys())
    extra_data = {
        key: default_extra_data.get(key) or non_default_extra_data.get(key) for key in all_keys
    }

    for item in extra_data:
        if item in default_extra_data and default_extra_data[item]:
            extra_data_sources[item] = default.pk
        elif item in non_default_extra_data and non_default_extra_data[item]:
            extra_data_sources[item] = non_default.pk
        else:
            extra_data_sources[item] = default.pk

    return extra_data, extra_data_sources


def merge_state(merged_state, state1, state2, can_attrs, default=None):
    """
    Set attributes on our Canonical model, saving differences.

    :param merged_state: PropertyState/TaxLotState model inst.
    :param state1: PropertyState/TaxLotState model inst. Left parent.
    :param state2: PropertyState/TaxLotState model inst. Right parent.
    :param can_attrs:  dict of dicts, {'attr_name': {'dataset1': 'value'...}}.
    :param default: (optional), which dataset's value to default to.
    :return: inst(``merged_state``), updated.
    """
    default = default or state2
    for attr in can_attrs:
        # Do we have any differences between these fields? - Check if not None instead of if value.
        attr_values = list(set([value for value in can_attrs[attr].values() if value is not None]))
        attr_values = [v for v in attr_values if v is not None]

        attr_value = None
        # Two, differing values are set.
        if len(attr_values) > 1:
            # If we have more than one value for this field, save each of the field options in the DB,
            # but opt for the default when there is a difference.
            attr_value = can_attrs[attr][default]

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

    merged_extra_data, merged_extra_data_sources = _merge_extra_data(state1, state2, default=default)
    merged_state.extra_data = merged_extra_data

    # merge measures, scenarios, simulations
    if isinstance(merged_state, PropertyState):
        PropertyState.merge_relationships(merged_state, state1, state2)

    return merged_state
