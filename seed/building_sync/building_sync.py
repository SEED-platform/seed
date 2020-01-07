# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

import copy
from datetime import datetime
import pytz
import json
import logging
import os
from builtins import str
from collections import OrderedDict

import xmltodict
from django.db.models import FieldDoesNotExist
from past.builtins import basestring
from quantityfield import ureg

from seed.models.measures import _snake_case
from seed.models.meters import Meter

_log = logging.getLogger(__name__)


class BuildingSync(object):
    ADDRESS_STRUCT = {
        "root": "auc:BuildingSync.auc:Facilities.auc:Facility.auc:Sites.auc:Site.auc:Address",
        "return": {
            "address_line_1": {
                "path": "auc:StreetAddressDetail.auc:Simplified.auc:StreetAddress",
                "required": True,
                "type": "string",
            },
            "city": {
                "path": "auc:City",
                "required": True,
                "type": "string",
            },
            "state": {
                "path": "auc:State",
                "required": True,
                "type": "string",
            }
        }
    }

    BRICR_STRUCT = {
        "root": "auc:BuildingSync.auc:Facilities.auc:Facility",
        "return": {
            "address_line_1": {
                "path": "auc:Sites.auc:Site.auc:Address.auc:StreetAddressDetail.auc:Simplified.auc:StreetAddress",
                "required": True,
                "type": "string",
            },
            "city": {
                "path": "auc:Sites.auc:Site.auc:Address.auc:City",
                "required": True,
                "type": "string",
            },
            "state": {
                "path": "auc:Sites.auc:Site.auc:Address.auc:State",
                "required": True,
                "type": "string",
            },
            "postal_code": {
                "path": "auc:Sites.auc:Site.auc:Address.auc:PostalCode",
                "required": True,
                "type": "string",
            },
            "longitude": {
                "path": "auc:Sites.auc:Site.auc:Longitude",
                "required": False,
                "type": "double"
            },
            "latitude": {
                "path": "auc:Sites.auc:Site.auc:Latitude",
                "required": False,
                "type": "double",
            },
            "property_name": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.@ID",
                "required": True,
                "type": "string",
            },
            "property_type": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:Sections.auc:Section.auc:OccupancyClassification",
                "required": True,
                "type": "string",
            },
            "year_built": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:YearOfConstruction",
                "required": True,
                "type": "integer",
            },
            "floors_above_grade": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorsAboveGrade",
                "required": False,
                "type": "integer",
            },
            "floors_below_grade": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorsBelowGrade",
                "required": False,
                "type": "integer",
            },
            "premise_identifier": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:PremisesIdentifiers.auc:PremisesIdentifier",
                "key_path_name": "auc:IdentifierLabel",
                "key_path_value": "Assessor parcel number",
                "value_path_name": "auc:IdentifierValue",
                "required": False,  # temporarily make this False until AT can handle it correctly.
                "type": "string",
            },
            "ubid": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:PremisesIdentifiers.auc:PremisesIdentifier",
                "key_path_name": "auc:IdentifierLabel",
                "key_path_value": "UBID",
                "value_path_name": "auc:IdentifierValue",
                "required": False,
                "type": "string",
            },
            "custom_id_1": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:PremisesIdentifiers.auc:PremisesIdentifier",
                "key_path_name": "auc:IdentifierCustomName",
                "key_path_value": "Custom ID 1",
                "value_path_name": "auc:IdentifierValue",
                "required": False,
                "type": "string",
            },
            "gross_floor_area": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorAreas.auc:FloorArea",
                "key_path_name": "auc:FloorAreaType",
                "key_path_value": "Gross",
                "value_path_name": "auc:FloorAreaValue",
                "required": True,
                "type": "double",
            },
            "net_floor_area": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorAreas.auc:FloorArea",
                "key_path_name": "auc:FloorAreaType",
                "key_path_value": "Net",
                "value_path_name": "auc:FloorAreaValue",
                "required": False,
                "type": "double",
            },
            "footprint_floor_area": {
                "path": "auc:Sites.auc:Site.auc:Buildings.auc:Building.auc:FloorAreas.auc:FloorArea",
                "key_path_name": "auc:FloorAreaType",
                "key_path_value": "Footprint",
                "value_path_name": "auc:FloorAreaValue",
                "required": False,
                "type": "double",
            },
        }
    }

    def __init__(self):
        self.filename = None
        self.data = None
        self.raw_data = {}

    @property
    def pretty_print(self):
        """
        Print the JSON to the screen
        :return: None
        """
        print(json.dumps(self.raw_data, indent=2))

    def import_file(self, filename):
        self.filename = filename

        if os.path.isfile(filename):
            with open(filename, 'rU') as xmlfile:
                self.raw_data = xmltodict.parse(
                    xmlfile.read(),
                    process_namespaces=True,
                    namespaces={
                        'http://buildingsync.net/schemas/bedes-auc/2019': 'auc',
                        'http://www.w3.org/2001/XMLSchema-instance': 'xsi',
                    }
                )

        else:
            raise Exception("File not found: {}".format(filename))

        return True

    def export(self, property_state, process_struct=ADDRESS_STRUCT):
        """Export BuildingSync file from an existing BuildingSync file (from import), property_state and
        a process struct.

        :param property_state: object, PropertyState to merge into BuildingSync
        :param process_struct: dict, mapping from PropertyState to BuildingSync
        :return: string, as XML
        """

        # if property state is not defined, then just return the BuildingSync unparsed
        if not property_state:
            return xmltodict.unparse(self.raw_data, pretty=True).replace('\t', '  ')

        # parse the property_state and merge it with the raw data
        new_dict = copy.deepcopy(self.raw_data)
        if new_dict == {}:
            _log.debug("BuildingSync raw data is empty, adding in header information")
            # new_dict[]
            new_dict = OrderedDict(
                [
                    (
                        'auc:BuildingSync', OrderedDict(
                            [
                                ('@xsi:schemaLocation',
                                 'http://buildingsync.net/schemas/bedes-auc/2019 https://github.com/BuildingSync/schema/releases/download/v1.0.0/BuildingSync.xsd'),
                                ('@xmlns', OrderedDict(
                                    [
                                        ('auc', 'http://buildingsync.net/schemas/bedes-auc/2019'),
                                        ('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                                    ]
                                ))
                            ]
                        )
                    )
                ]
            )
        else:
            # check that the appropriate headers are set or XML won't render correctly in the browser
            if '@xsi:schemaLocation' not in new_dict['auc:BuildingSync'] or '@xmlns' not in new_dict['auc:BuildingSync']:
                new_dict['auc:BuildingSync']['@xsi:schemaLocation'] = 'http://buildingsync.net/schemas/bedes-auc/2019 https://github.com/BuildingSync/schema/releases/download/v1.0.0/BuildingSync.xsd'
                new_dict['auc:BuildingSync']['@xmlns'] = OrderedDict
                (
                    [
                        ('auc', 'http://buildingsync.net/schemas/bedes-auc/2019'),
                        ('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
                    ]
                )

        for field, v in process_struct['return'].items():
            value = None
            try:
                property_state._meta.get_field(field)
                value = getattr(property_state, field)
            except FieldDoesNotExist:
                _log.debug("Field {} is not a db field, trying read from extra data".format(field))
                value = property_state.extra_data.get(field, None)

            # set the value in the new_dict (if none, then remove the field)
            # TODO: remove the field if the value is None
            # TODO: handle the setting of the complex fields (with key_path_names, identifiers)
            if value:
                full_path = "{}.{}".format(process_struct['root'], v['path'])

                if v.get('key_path_name', None) and v.get('value_path_name', None) and v.get('key_path_value', None):
                    # iterate over the paths and find the correct node to set
                    self._set_compound_node(
                        full_path,
                        new_dict,
                        v['key_path_name'],
                        v['key_path_value'],
                        v['value_path_name'],
                        value
                    )
                else:
                    if not self._set_node(full_path, new_dict, value):
                        _log.debug("Unable to set path")

        return xmltodict.unparse(new_dict, pretty=True).replace('\t', '  ')

    def _set_node(self, path, data, value):
        """
        Set the value in the dictionary based on the path. If there are more than one paths, then
        it will only set the first path for now. The future could allow a variable to pass in the
        index (or other constraint) before setting the value.

        :param path: string, path which to navigate to set the value
        :param data: dict, dictionary to process
        :param value: value to set, could be any type at the moment.
        :return: boolean, true if successful
        """

        path = path.split(".")
        for idx, p in enumerate(path):
            if p == '':
                return False
            elif idx == len(path) - 1:
                if value is None:
                    del data[p]
                else:
                    data[p] = value
                return True
            else:
                prev_node = path.pop(0)
                new_node = data.get(prev_node)
                new_path = '.'.join(path)
                if new_node is None:
                    # create the new node because it doesn't exist
                    data[prev_node] = {}
                    new_node = data[prev_node]

                if isinstance(new_node, list):
                    _log.debug("Unable to iterate over lists at the moment")
                    return False
                elif isinstance(new_node, dict):
                    return self._set_node(new_path, new_node, value)
                else:
                    # can't recurse futher into new_node because it is not a dict
                    break

    def _set_compound_node(self, list_path, data, key_path_name, key_path_value, value_path_name,
                           value):
        """
        If the XML is a list of options with a key field at the same level as the value, then use
        this method. The example belows show how the XML will be structured. To set the
        Gross floor area, then pass in the following

            _set_compound_node("...FloorAreas", "FloorAreaType", "Gross", "FloorAreaValue", 1000)

        .. code:

            <auc:FloorAreas>
                <auc:FloorArea>
                    <auc:FloorAreaType>Gross</auc:FloorAreaType>
                    <auc:FloorAreaValue>25000</auc:FloorAreaValue>
                </auc:FloorArea>
                <auc:FloorArea>
                    <auc:FloorAreaType>Net</auc:FloorAreaType>
                    <auc:FloorAreaValue>22500</auc:FloorAreaValue>
                </auc:FloorArea>
            </auc:FloorAreas>

        :param list_path: String, path to where the list of items start in the dictionary
        :param data: Dict, data to act on
        :param key_path_name: String, name of the element to contrain check on
        :param key_path_value: String, name of the value of the element to check on
        :param value_path_name: String, name of the element that will be set
        :param value: undefined, Value to set
        :return: Boolean
        """

        path = list_path.split(".")
        for idx, p in enumerate(path):
            if p == '':
                return False
            elif idx == len(path) - 1:
                # We have arrived at the location where the compound data needs to be set
                # Make sure that the key_path_name and key_path_value are not already there
                if data.get(p):
                    if isinstance(data[p], dict):
                        if data[p].get(key_path_name) == key_path_value:
                            if isinstance(value, ureg.Quantity):
                                data[p][value_path_name] = value.magniture
                            else:
                                data[p][value_path_name] = value
                        else:
                            # need to convert the dict to a list and then add the new one.
                            data[p] = [data[p]]
                            new_sub_item = {key_path_name: key_path_value, value_path_name: value}
                            data[p].append(new_sub_item)
                    elif isinstance(data[p], list):
                        for sub in data[p]:
                            if sub.get(key_path_name, None) == key_path_value:
                                if isinstance(value, ureg.Quantity):
                                    sub[value_path_name] = value.magnitude
                                else:
                                    sub[value_path_name] = value

                                break
                        else:
                            # Not found, create a new one
                            if isinstance(value, ureg.Quantity):
                                new_sub_item = {
                                    key_path_name: key_path_value,
                                    value_path_name: value.magnitude
                                }
                            else:
                                new_sub_item = {
                                    key_path_name: key_path_value,
                                    value_path_name: value
                                }
                            data[p].append(new_sub_item)
                else:
                    if isinstance(value, ureg.Quantity):
                        data[p] = {key_path_name: key_path_value, value_path_name: value.magnitude}
                    else:
                        data[p] = {key_path_name: key_path_value, value_path_name: value}

                return True
            else:
                prev_node = path.pop(0)
                new_node = data.get(prev_node)
                new_path = '.'.join(path)
                if new_node is None:
                    # create the new node because it doesn't exist
                    data[prev_node] = {}
                    new_node = data[prev_node]

                if isinstance(new_node, list):
                    _log.debug("Unable to iterate over lists at the moment")
                    return False
                elif isinstance(new_node, dict):
                    return self._set_compound_node(new_path, new_node, key_path_name,
                                                   key_path_value, value_path_name, value)
                else:
                    # can't recurse futher into new_node because it is not a dict
                    break

    def _get_node(self, path, node, results=[], kwargs={}):
        """
        Return the values from a dictionary based on a path delimited by periods. If there
        are more than one results, then it will return all the results in a list.

        The method handles nodes that are either lists or either dictionaries. This method is
        recursive as it nagivates the tree.

        :param path: string, path which to navigate to in the dictionary
        :param node: dict, dictionary to process
        :param results: list or value, results
        :return: list, results
        """

        path = path.split(".")

        for idx, p in enumerate(path):

            if p == '':
                if node:
                    results.append(node)
                break
            elif idx == len(path) - 1:
                value = node.get(p)
                if value:
                    results.append(node.get(p))
                break
            else:
                new_node = node.get(path.pop(0))
                new_path = '.'.join(path)
                if isinstance(new_node, list):
                    # grab the values from each item in the list or iterate
                    for nn in new_node:
                        self._get_node(new_path, nn, results)
                    break
                elif isinstance(new_node, dict):
                    self._get_node(new_path, new_node, results)
                    break
                else:
                    # can't recurse futher into new_node because it is not a dict
                    break

        if len(results) == 0:
            return []
        elif len(results) == 1:
            return results[0]
        else:
            return results

    def _process_struct(self, struct, data):
        """
        Take a dictionary and return the `return` object with values filled in.

        :param struct: dict, object to parse and fill from BuildingSync file
        :param data: dict, data to parse and fill
        :return: list, the `return` value, if all paths were found, and list of messages
        """
        def _lookup_sub(node, key_path_name, key_path_value, value_path_name):
            items = [node] if isinstance(node, dict) else node
            for item in items:
                found = False
                for k, v in item.items():
                    if k == key_path_name and v == key_path_value:
                        found = True

                    if found and k == value_path_name:
                        return v

        res = {'measures': [], 'scenarios': []}
        messages = {'errors': [], 'warnings': []}

        for k, v in struct['return'].items():
            path = ".".join([struct['root'], v['path']])
            value = self._get_node(path, data, [])

            try:
                if v.get('key_path_name', None) and v.get('value_path_name', None) and v.get('key_path_value', None):
                    value = _lookup_sub(
                        value,
                        v.get('key_path_name'),
                        v.get('key_path_value'),
                        v.get('value_path_name'),
                    )

                    # check if the value is not defined and if it is required
                    if not value:
                        if v.get('required'):
                            messages['errors'].append(
                                "Could not find required value for sub-lookup of {}:{}".format(
                                    v.get('key_path_name'), v.get('key_path_value')))
                            continue
                        else:
                            continue

                if value:
                    # catch some errors
                    if isinstance(value, list):
                        messages['errors'].append(
                            "Could not find single entry for '{}'".format(path)
                        )
                        continue

                    # type cast the value
                    if v['type'] == 'double':
                        value = float(value)
                    elif v['type'] == 'integer':
                        value = int(value)
                    elif v['type'] == 'dict':
                        value = dict(value)
                    elif v['type'] == 'string':
                        value = str(value)
                    else:
                        messages['errors'].append(
                            "Unknown cast type of {} for '{}'".format(v['type'], path)
                        )

                    res[k] = value
                else:
                    if v['required']:
                        messages['errors'].append(
                            "Could not find required value for '{}'".format(path)
                        )
            except Exception as err:
                message = "Error processing {}:{} with error: {}".format(k, v, err)
                messages['errors'].append(message)

        # manually add in parsing of measures and reports because they are a bit different than
        # a straight mapping
        # <auc:Measure ID="Measure-70165601915860">
        #   <auc:SystemCategoryAffected>Plug Load</auc:SystemCategoryAffected>
        #   <auc:TechnologyCategories>
        #     <auc:TechnologyCategory>
        #       <auc:PlugLoadReductions>
        #         <auc:MeasureName>Replace with ENERGY STAR rated</auc:MeasureName>
        #       </auc:PlugLoadReductions>
        #     </auc:TechnologyCategory>
        #   </auc:TechnologyCategories>
        #   <auc:LongDescription>Replace with ENERGY STAR rated</auc:LongDescription>
        #   <auc:MVCost>0.0</auc:MVCost>
        #   <auc:UsefulLife>20.0</auc:UsefulLife>
        #   <auc:MeasureTotalFirstCost>5499.0</auc:MeasureTotalFirstCost>
        #   <auc:MeasureInstallationCost>0.0</auc:MeasureInstallationCost>
        #   <auc:MeasureMaterialCost>0.0</auc:MeasureMaterialCost>
        # </auc:Measure>
        measures = self._get_node('auc:BuildingSync.auc:Facilities.auc:Facility.auc:Measures.auc:Measure', data, [])
        # check that this is a list, if not, make it a list or the loop won't work correctly
        if isinstance(measures, dict):
            # print("measures is a dict...converting it to a list")
            measures_tmp = []
            measures_tmp.append(measures)
            measures = measures_tmp
        for m in measures:
            if m.get('auc:TechnologyCategories', None):
                cat_w_namespace = list(m['auc:TechnologyCategories']['auc:TechnologyCategory'].keys())[0]
                category = cat_w_namespace.replace('auc:', '')
                new_data = {
                    'property_measure_name': m.get('@ID'),
                    # This will be the IDref from the scenarios
                    'category': _snake_case(category),
                    'name':
                        m['auc:TechnologyCategories']['auc:TechnologyCategory'][cat_w_namespace][
                            'auc:MeasureName']
                }
                for k, v in m.items():
                    if k in ['@ID', 'auc:PremisesAffected', 'auc:TechnologyCategories']:
                        continue
                    new_data[_snake_case(k.replace('auc:', ''))] = v

                # fix the names of the measures for "easier" look up... doing in separate step to
                # fit in single line. Cleanup -- when?
                new_data['name'] = _snake_case(new_data['name'])
                res['measures'].append(new_data)
            else:
                message = "Skipping measure %s due to missing TechnologyCategory" % m.get("@ID")
                messages['warnings'].append(message)

        # <auc:Scenario>
        #   <auc:ScenarioName>Lighting Only</auc:ScenarioName>
        #   <auc:ScenarioType>
        #     <auc:PackageOfMeasures>
        #       <auc:ReferenceCase IDref="Baseline"/>
        #       <auc:MeasureIDs>
        #         <auc:MeasureID IDref="Measure1"/>
        #       </auc:MeasureIDs>
        #       <auc:AnnualSavingsSiteEnergy>162654.89601696888</auc:AnnualSavingsSiteEnergy>
        #     </auc:PackageOfMeasures>
        #   </auc:ScenarioType>
        # </auc:Scenario>

        # KAF: for now, handle both Reports.Report and Report
        scenarios = self._get_node('auc:BuildingSync.auc:Facilities.auc:Facility.auc:Reports.auc:Report.auc:Scenarios.auc:Scenario', data, [])
        if not scenarios:
            scenarios = self._get_node('auc:BuildingSync.auc:Facilities.auc:Facility.auc:Report.auc:Scenarios.auc:Scenario', data, [])

        # check that this is a list; if not, make it a list or the loop won't work correctly
        if isinstance(scenarios, dict):
            # print("scenarios is a dict (only found 1...converting it to a list)")
            scenarios_tmp = []
            scenarios_tmp.append(scenarios)
            scenarios = scenarios_tmp

        for s in scenarios:
            new_data = {
                'id': s.get('@ID'),
                'name': s.get('auc:ScenarioName'),
            }

            if s.get('auc:ScenarioType'):
                node = s['auc:ScenarioType'].get('auc:PackageOfMeasures')
                if node:
                    ref_case = self._get_node('auc:ReferenceCase', node, [])
                    if ref_case and ref_case.get('@IDref'):
                        new_data['reference_case'] = ref_case.get('@IDref')
                    # fixed naming of existing scenario fields
                    new_data['annual_site_energy_savings'] = node.get('auc:AnnualSavingsSiteEnergy')
                    new_data['annual_source_energy_savings'] = node.get('auc:AnnualSavingsSourceEnergy')
                    new_data['annual_cost_savings'] = node.get('auc:AnnualSavingsCost')

                    # new scenario fields
                    fuel_savings = node.get('auc:AnnualSavingsByFuels')
                    if fuel_savings:
                        fuel_nodes = fuel_savings.get('auc:AnnualSavingsByFuel')
                        if isinstance(fuel_nodes, dict):
                            fuel_savings_arr = []
                            fuel_savings_arr.append(fuel_nodes)
                            fuel_nodes = fuel_savings_arr

                        for f in fuel_nodes:
                            if f.get('auc:EnergyResource') == 'Electricity':
                                new_data['annual_electricity_savings'] = f.get('auc:AnnualSavingsNativeUnits')
                                # print("ELECTRICITY: {}".format(new_data['annual_electricity_savings']))
                            elif f.get('auc:EnergyResource') == 'Natural gas':
                                new_data['annual_natural_gas_savings'] = f.get('auc:AnnualSavingsNativeUnits')
                                # print("GAS: {}".format(new_data['annual_natural_gas_savings']))

                    all_resources = s.get('auc:AllResourceTotals')
                    if all_resources:
                        resource_nodes = all_resources.get('auc:AllResourceTotal')
                        # print("ANNUAL ENERGY: {}".format(resource_nodes))
                        # make it an array
                        if isinstance(resource_nodes, dict):
                            resource_nodes_arr = []
                            resource_nodes_arr.append(resource_nodes)
                            resource_nodes = resource_nodes_arr

                        for rn in resource_nodes:
                            if rn.get('auc:EndUse') == 'All end uses':
                                new_data['annual_site_energy'] = rn.get('auc:SiteEnergyUse')
                                new_data['annual_site_energy_use_intensity'] = rn.get('auc:SiteEnergyUseIntensity')
                                new_data['annual_source_energy'] = rn.get('auc:SourceEnergyUse')
                                new_data['annual_source_energy_use_intensity'] = rn.get('auc:SourceEnergyUseIntensity')

                    resources = []
                    resource_uses = s.get('auc:ResourceUses')
                    if resource_uses:
                        ru_nodes = resource_uses.get('auc:ResourceUse')
                        # print("ResourceUse: {}".format(ru_nodes))

                        if isinstance(ru_nodes, dict):
                            ru_nodes_arr = []
                            ru_nodes_arr.append(ru_nodes)
                            ru_nodes = ru_nodes_arr

                        for ru in ru_nodes:

                            # store resourceID and EnergyResource  -- needed for TimeSeries
                            r = {}
                            r['id'] = ru.get('@ID')
                            r['type'] = ru.get('auc:EnergyResource')
                            r['units'] = ru.get('auc:ResourceUnits')
                            resources.append(r)

                            # just do these 2 types for now
                            if ru.get('auc:EnergyResource') == 'Electricity':
                                new_data['annual_electricity_energy'] = ru.get('auc:AnnualFuelUseConsistentUnits')  # in MMBtu
                                # get demand as well
                                new_data['annual_peak_demand'] = ru.get('auc:AnnualPeakConsistentUnits')  # in KW
                            elif ru.get('auc:EnergyResource') == 'Natural gas':
                                new_data['annual_natural_gas_energy'] = ru.get('auc:AnnualFuelUseConsistentUnits')  # in MMBtu

                    # timeseries
                    timeseriesdata = s.get('auc:TimeSeriesData')

                    # need to know if CalculationMethod is modeled (for meters)
                    isVirtual = False
                    calcMethod = node.get('auc:CalculationMethod')
                    if calcMethod is not None:
                        isModeled = calcMethod.get('auc:Modeled')
                        if isModeled is not None:
                            isVirtual = True

                    if timeseriesdata:
                        timeseries = timeseriesdata.get('auc:TimeSeries')

                        if isinstance(timeseries, dict):
                            ts_nodes_arr = []
                            ts_nodes_arr.append(timeseries)
                            timeseries = ts_nodes_arr

                        new_data['meters'] = []
                        for ts in timeseries:
                            source_id = ts.get('auc:ResourceUseID').get('@IDref')
                            # print("SOURCE ID: {}".format(source_id))
                            source_unit = next((item for item in resources if item['id'] == source_id), None)
                            source_unit = source_unit['units'] if source_unit is not None else None
                            match = next((item for item in new_data['meters'] if item['source_id'] == source_id), None)
                            if match is None:
                                # this source_id is not yet in meters, add it
                                meter = {}
                                meter['source_id'] = source_id
                                source = next((item for item in Meter.SOURCES if item[1] == 'BuildingSync'), None)
                                meter['source'] = source[0]  # for BuildingSync
                                meter['is_virtual'] = isVirtual

                                typeMatch = next((item for item in resources if item['id'] == source_id), None)
                                typeMatch = typeMatch['type'].title() if typeMatch is not None else None
                                # print("TYPE MATCH: {}".format(type_match))
                                # For "Electricity", match on 'Electric - Grid'
                                tmp_type = "Electric - Grid" if typeMatch == 'Electricity' else typeMatch
                                theType = next((item for item in Meter.ENERGY_TYPES if item[1] == tmp_type), None)
                                # print("the type: {}".format(the_type))
                                theType = theType[0] if theType is not None else None
                                meter['type'] = theType
                                meter['readings'] = []
                                new_data['meters'].append(meter)

                            # add reading connected to meter (use resourceID/source_id for matching)
                            reading = {}
                            # ignoring timezones...pretending all is in UTC for DB and Excel export
                            reading['start_time'] = pytz.utc.localize(datetime.strptime(ts.get('auc:StartTimeStamp'), "%Y-%m-%dT%H:%M:%S"))
                            reading['end_time'] = pytz.utc.localize(datetime.strptime(ts.get('auc:EndTimeStamp'), "%Y-%m-%dT%H:%M:%S"))
                            reading['reading'] = ts.get('auc:IntervalReading')
                            reading['source_id'] = source_id
                            reading['source_unit'] = source_unit
                            # append to appropriate meter (or don't import)
                            the_meter = next((item for item in new_data['meters'] if item['source_id'] == source_id), None)
                            if the_meter is not None:
                                the_meter['readings'].append(reading)

                        # print("METERS: {}".format(new_data['meters']))

                    # measures
                    new_data['measures'] = []
                    measures = self._get_node('auc:MeasureIDs.auc:MeasureID', node, [])
                    if isinstance(measures, list):
                        for measure in measures:
                            if measure.get('@IDref', None):
                                new_data['measures'].append(measure.get('@IDref'))
                    else:
                        if isinstance(measures, basestring):
                            # the measure is there, but it does not have an idref
                            continue
                        else:
                            if measures.get('@IDref', None):
                                new_data['measures'].append(measures.get('@IDref'))

            res['scenarios'].append(new_data)

        # print("SCENARIOS: {}".format(res['scenarios']))

        return res, messages

    def process(self, process_struct=ADDRESS_STRUCT):
        """Process the BuildingSync file based on the process structure.

        :param process_struct: dict, structure on how to extract data from file and save into dict
        :return: list, [dict, dict], [results, dict of errors and warnings]
        """
        # API call to BuildingSync Selection Tool on other server for appropriate use case
        # prcess_struct = new_use_case (from Building Selection Tool)
        return self._process_struct(process_struct, self.raw_data)
