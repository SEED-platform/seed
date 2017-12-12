# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""
import copy
import logging
from collections import defaultdict

from django.db import IntegrityError
from django.forms.models import model_to_dict

from seed.lib.mappings.mapping_data import MappingData
from seed.models import (
    PropertyState,
    TaxLotState,
    Simulation,
    PropertyMeasure,
    Scenario,
)
from seed.utils.mapping import get_mappable_columns

LINEAR_UNITS = {u'ft', u'm', u'in'}

# TODO: Fix name of this method / remove if possible.
BuildingSnapshot_to_BuildingSnapshot = tuple([(k, k) for k in get_mappable_columns()])

md = MappingData()
property_state_fields = [x['name'] for x in md.property_data]
tax_lot_state_fields = [x['name'] for x in md.tax_lot_data]

PropertyState_to_PropertyState = tuple([(k, k) for k in property_state_fields])
TaxLotState_to_TaxLotState = tuple([(k, k) for k in tax_lot_state_fields])

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


def get_propertystate_attrs(data_set_buildings):
    # Old school approach.
    mapping = BuildingSnapshot_to_BuildingSnapshot
    return get_attrs_with_mapping(data_set_buildings, mapping)


def get_taxlotstate_attrs(data_set_buildings):
    mapping = TaxLotState_to_TaxLotState
    return get_attrs_with_mapping(data_set_buildings, mapping)


def get_state_attrs(state_list):
    if not state_list:
        return []

    if isinstance(state_list[0], PropertyState):
        return get_propertystate_attrs(state_list)
    elif isinstance(state_list[0], TaxLotState):
        return get_taxlotstate_attrs(state_list)


def _merge_relationships(merged_state, state1, state2):
    """
    Merge together the old relationships with the new.
    """
    # get some items off of this property view
    no_measure_scenarios = [x for x in state2.scenarios.filter(measures__isnull=True)] + \
        [x for x in state1.scenarios.filter(measures__isnull=True)]
    building_files = [x for x in state2.building_files.all()] + [x for x in state1.building_files.all()]
    simulations = [x for x in Simulation.objects.filter(property_state__in=[state1, state2])]
    measures = [x for x in PropertyMeasure.objects.filter(property_state__in=[state1, state2])]

    # TODO: dedup the relationships, if they are exact then don't add

    # copy in the no measure scenarios
    for new_s in no_measure_scenarios:
        new_s.pk = None
        new_s.save()
        merged_state.scenarios.add(new_s)

    for new_bf in building_files:
        new_bf.pk = None
        new_bf.save()
        merged_state.building_files.add(new_bf)

    for new_sim in simulations:
        new_sim.pk = None
        new_sim.property_state = merged_state
        new_sim.save()

    if len(measures) > 0:
        measure_fields = [f.name for f in measures[0]._meta.fields]
        measure_fields.remove('id')
        measure_fields.remove('property_state')

        new_items = []

        # Create a list of scenarios and measures to reconstruct
        # {
        #   scenario_id_1: [ new_measure_id_1, new_measure_id_2 ],
        #   scenario_id_2: [ new_measure_id_2, new_measure_id_3 ],  # measure ids can be repeated
        # }
        scenario_measure_map = {}
        for measure in measures:
            test_dict = model_to_dict(measure, fields=measure_fields)

            if test_dict in new_items:
                continue
            else:
                try:
                    new_measure = copy.deepcopy(measure)
                    new_measure.pk = None
                    new_measure.property_state = merged_state
                    new_measure.save()

                    # grab the scenario that is attached to the orig measure and create a new connection
                    for scenario in measure.scenario_set.all():
                        if scenario.pk not in scenario_measure_map.keys():
                            scenario_measure_map[scenario.pk] = []
                        scenario_measure_map[scenario.pk].append(new_measure.pk)

                except IntegrityError:
                    _log.error(
                        "Measure state_id, measure_id, application_sacle, and implementation_status already exists -- skipping for now")

            new_items.append(test_dict)

        # connect back up the scenario measures
        for scenario_id, measure_list in scenario_measure_map.items():
            # create a new scenario from the old one
            scenario = Scenario.objects.get(pk=scenario_id)
            scenario.pk = None
            scenario.property_state = merged_state
            scenario.save()  # save to get new id

            # get the measures
            measures = PropertyMeasure.objects.filter(pk__in=measure_list)
            for measure in measures:
                scenario.measures.add(measure)
            scenario.save()

    return merged_state


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

    merged_extra_data, merged_extra_data_sources = _merge_extra_data(state1, state2, default=default)
    merged_state.extra_data = merged_extra_data

    # merge measures, scenarios,
    if isinstance(merged_state, PropertyState):
        _merge_relationships(merged_state, state1, state2)

    return merged_state, changes
