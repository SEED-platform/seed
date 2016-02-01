# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from collections import defaultdict

from seed.mappings import seed_mappings
from seed import models


def save_variant(snapshot, attr, attribute_values):
    """Save different options from each dataset for a Canonical field value.

    :param snapshot: BuildingSnapshot inst.
    :param attr: string, the disputed attribute on the can_building inst.
    :attribute_values: dict of obj:str. Keyed on datasource model instance.

    """
    variant, created = models.BuildingAttributeVariant.objects.get_or_create(
        field_name=attr,
        building_snapshot=snapshot
    )

    for data_set in attribute_values:
        if attribute_values[data_set] is None:
            continue

        data_source_id = get_source_id(data_set, attr)
        option, op_created = models.AttributeOption.objects.get_or_create(
            value=attribute_values[data_set],
            value_source=data_source_id
        )
        if op_created:
            variant.options.add(option)

    return variant


def get_attr_source(field_values, value):
    """Return the first dictionary key that contains a value."""
    return (k for k, v in field_values.items() if v == value).next()


def get_source_id(source_inst, attr):
    """Get the ID we save for our model source from ``models`` module."""
    default = 2  # BuildingSnapshot
    # Because we cannot FK directly to BuildingSnapshots we have to
    # painstakingly copy whatever the original reference to this field
    # out of the BS and into the BuildingAttributeVariant.
    if isinstance(source_inst, models.BuildingSnapshot):
        source_inst = getattr(source_inst, '{0}_source'.format(attr))

    return getattr(
        models, '{0}_SOURCE'.format(source_inst.__class__.__name__), default
    )


def merge_extra_data(b1, b2, default=None):
    """Merge extra_data field between two BuildingSnapshots, return result.

    :param b1: BuildingSnapshot inst.
    :param b2: BuildingSnapshot inst.
    :param default: BuildingSnapshot inst.

    :returns tuple of dict:
        first dict contains values, second the source pks.
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


def merge_building(
    snapshot, b1, b2, can_attrs, conf, default=None, match_type=None
):
    """Set attributes on our Canonical model, saving differences.

    :param snapshot: BuildingSnapshot model inst.
    :param b1: BuildingSnapshot model inst. Left parent.
    :param b2: BuildingSnapshot model inst. Right parent.
    :param can_attrs: dict of dicts, {'attr_name': {'dataset1': 'value'...}}.
    :param default: (optional), which dataset's value to default to.
    :rtype BuildingSnapshot inst(``snapshot``), updated.

    """
    default = default or b1
    match_type = match_type or models.SYSTEM_MATCH
    changes = []
    for attr in can_attrs:
        # Do we have any differences between these fields?
        attr_values = list(set([
            value for value in can_attrs[attr].values() if value
        ]))

        attr_value = None
        # Two, differing values are set.
        if len(attr_values) > 1:
            # If we have more than one value for this field,
            # save each of the field options in the DB,
            # but opt for the default when there is a difference.
            save_variant(snapshot, attr, can_attrs[attr])
            attr_source = default
            attr_value = can_attrs[attr][default]

            if attr_values[0] != attr_values[1]:
                changes.append({"field": attr, "from": attr_values[0], "to": attr_values[1]})

        # No values are set
        elif len(attr_values) < 1:
            attr_value = None
            attr_source = None

        # There is only one value set.
        else:
            attr_value = attr_values.pop()
            # Get the correct key from the sub dictionary to indicate
            # the source of a field value.
            attr_source = get_attr_source(can_attrs[attr], attr_value)

        if callable(attr):
            # This callable will be responsible for setting
            # the attribute value, not just returning it.
            attr(snapshot, default)
        else:
            setattr(snapshot, attr, attr_value)
            setattr(snapshot, '{0}_source'.format(attr), attr_source)

    snapshot.extra_data, snapshot.extra_data_sources = merge_extra_data(
        b1, b2, default=default
    )
    snapshot.match_type = match_type
    snapshot.source_type = models.COMPOSITE_BS
    canonical_building = models.get_or_create_canonical(b1, b2)
    snapshot.canonical_building = canonical_building
    snapshot.confidence = conf
    snapshot.save()

    canonical_building.canonical_snapshot = snapshot
    canonical_building.save()
    b1.children.add(snapshot)
    b2.children.add(snapshot)

    return snapshot, changes


def get_building_attrs(data_set_buildings):
    """Returns a dictionary of attributes from each data_set_building.

    :param buildings: list, group of BS instances to merge.
    :rtype BuildingSnapshot dict: possible attributes keyed on attr name.
        Ex:
        {'property_name': {building_inst1: 'value', building_inst2: 'value2'}}

    """
    can_attrs = defaultdict(dict)
    mapping = seed_mappings.BuildingSnapshot_to_BuildingSnapshot
    for data_set_building in data_set_buildings:
        for data_set_attr, can_attr in mapping:
            data_set_value = getattr(data_set_building, data_set_attr)
            can_attrs[can_attr][data_set_building] = data_set_value

    return can_attrs
