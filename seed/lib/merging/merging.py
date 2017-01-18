# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""
import logging
from collections import defaultdict

from seed.models import PropertyState
from seed.models import TaxLotState

LINEAR_UNITS = set([u'ft', u'm', u'in'])  # ??more??

from seed.utils.mapping import get_mappable_columns
from seed.lib.mappings.mapping_data import MappingData
from seed.models.deprecate import SYSTEM_MATCH

# TODO: Fix name of this method / remove if possible.
BuildingSnapshot_to_BuildingSnapshot = tuple([(k, k) for k in get_mappable_columns()])

md = MappingData()
property_state_fields = [x['name'] for x in md.property_data]
tax_lot_state_fields = [x['name'] for x in md.tax_lot_data]

PropertyState_to_PropertyState = tuple([(k, k) for k in property_state_fields])
TaxLotState_to_TaxLotState = tuple([(k, k) for k in tax_lot_state_fields])

_log = logging.getLogger(__name__)


def get_attrs_with_mapping(data_set_buildings, mapping):
    """Returns a dictionary of attributes from each data_set_building.

    :param buildings: list, group of BS instances to merge.
    :return: BuildingSnapshot dict: possible attributes keyed on attr name.

    .. code-block::python

        {
            'property_name': {
                building_inst1: 'value', building_inst2: 'value2'
            }
        }

    """

    can_attrs = defaultdict(dict)
    # mapping = seed_mappings.BuildingSnapshot_to_BuildingSnapshot
    for data_set_building in data_set_buildings:
        for data_set_attr, can_attr in mapping:
            data_set_value = getattr(data_set_building, data_set_attr)
            can_attrs[can_attr][data_set_building] = data_set_value

    return can_attrs


def get_propertystate_attrs(data_set_buildings):
    # Old school approach.
    mapping = BuildingSnapshot_to_BuildingSnapshot
    return get_attrs_with_mapping(data_set_buildings, mapping)


def get_taxlotstate_attrs(data_set_buildings):
    MappingData()
    mapping = TaxLotState_to_TaxLotState
    return get_attrs_with_mapping(data_set_buildings, mapping)


def get_state_attrs(state_list):
    if not state_list:
        return []

    if isinstance(state_list[0], PropertyState):
        return get_propertystate_attrs(state_list)
    elif isinstance(state_list[0], TaxLotState):
        return get_taxlotstate_attrs(state_list)


def merge_extra_data(b1, b2, default=None):
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
        k: default_extra_data.get(k) or non_default_extra_data.get(k)
        for k in all_keys
    }

    for item in extra_data:
        if item in default_extra_data and default_extra_data[item]:
            extra_data_sources[item] = default.pk
        elif item in non_default_extra_data and non_default_extra_data[item]:
            extra_data_sources[item] = non_default.pk
        else:
            extra_data_sources[item] = default.pk

    return extra_data, extra_data_sources


def merge_state(merged_state, state1, state2, can_attrs, conf, default=None, match_type=None):
    """Set attributes on our Canonical model, saving differences.

    :param merged_state: PropertyState/TaxLotState model inst.
    :param state1: PropertyState/TaxLotState model inst. Left parent.
    :param state2: PropertyState/TaxLotState model inst. Right parent.
    :param can_attrs: dict of dicts, {'attr_name': {'dataset1': 'value'...}}.
    :param default: (optional), which dataset's value to default to.
    :return: inst(``merged_state``), updated.

    """
    default = default or state2
    match_type = match_type or SYSTEM_MATCH
    changes = []
    for attr in can_attrs:
        # Do we have any differences between these fields?
        attr_values = list(set([
            value for value in can_attrs[attr].values() if value
        ]))
        attr_values = [v for v in attr_values if v is not None]

        attr_value = None
        # Two, differing values are set.
        if len(attr_values) > 1:
            # If we have more than one value for this field,
            # save each of the field options in the DB,
            # but opt for the default when there is a difference.

            # WTF is this?
            # save_variant(merged_state, attr, can_attrs[attr])
            # attr_source = default
            attr_value = can_attrs[attr][default]

            # if attr_values[0] != attr_values[1]:
            #     changes.append({"field": attr, "from": attr_values[0], "to": attr_values[1]})

        # No values are set
        elif len(attr_values) < 1:
            attr_value = None
            # attr_source = None

        # There is only one value set.
        else:
            attr_value = attr_values.pop()
            # Get the correct key from the sub dictionary to indicate
            # the source of a field value.
            # attr_source = get_attr_source(can_attrs[attr], attr_value)

        if callable(attr):
            # This callable will be responsible for setting
            # the attribute value, not just returning it.
            attr(merged_state, default)
        else:
            setattr(merged_state, attr, attr_value)
            # setattr(merged_state, '{0}_source'.format(attr), attr_source)

    # TODO - deprecate extra_data_sources
    # pdb.set_trace()
    merged_extra_data, merged_extra_data_sources = merge_extra_data(state1, state2, default=default)

    merged_state.extra_data = merged_extra_data

    return merged_state, changes
