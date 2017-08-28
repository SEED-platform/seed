# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

import json
import os

import xmltodict

from seed.models.measures import _snake_case


class BuildingSync(object):
    ADDRESS_STRUCT = {
        "root": "Audits.Audit.Sites.Site.Address",
        "return": {
            "address_line_1": {
                "path": "StreetAddressDetail.Simplified.StreetAddress",
                "required": True,
                "type": "string",
            },
            "city": {
                "path": "City",
                "required": True,
                "type": "string",
            },
            "state": {
                "path": "State",
                "required": True,
                "type": "string",
            }
        }
    }

    BRICR_STRUCT = {
        "root": "Audits.Audit",
        "return": {
            "address_line_1": {
                "path": "Sites.Site.Address.StreetAddressDetail.Simplified.StreetAddress",
                "required": True,
                "type": "string",
            },
            "city": {
                "path": "Sites.Site.Address.City",
                "required": True,
                "type": "string",
            },
            "state": {
                "path": "Sites.Site.Address.State",
                "required": True,
                "type": "string",
            },
            "longitude": {
                "path": "Sites.Site.Longitude",
                "required": True,
                "type": "double"
            },
            "latitude": {
                "path": "Sites.Site.Latitude",
                "required": True,
                "type": "double",
            },
            "property_name": {
                "path": "Sites.Site.Facilities.Facility.@ID",
                "required": True,
                "type": "string",
            },
            "year_built": {
                "path": "Sites.Site.Facilities.Facility.YearOfConstruction",
                "required": True,
                "type": "integer",
            },
            "property_type": {
                "path": "Sites.Site.Facilities.Facility.FacilityClassification",
                "required": True,
                "type": "string",
            },
            "occupancy_type": {
                "path": "Sites.Site.Facilities.Facility.OccupancyClassification",
                "required": True,
                "type": "string",
            },
            "floors_above_grade": {
                "path": "Sites.Site.Facilities.Facility.FloorsAboveGrade",
                "required": True,
                "type": "integer",
            },
            "floors_below_grade": {
                "path": "Sites.Site.Facilities.Facility.FloorsBelowGrade",
                "required": True,
                "type": "integer",
            },
            "premise_identifier": {
                "path": "Sites.Site.Facilities.Facility.PremisesIdentifiers.PremisesIdentifier",
                "key_path_name": "IdentifierLabel",
                "key_path_value": "Assessor parcel number",
                "value_path_name": "IdentifierValue",
                "required": True,
                "type": "string",
            },
            "custom_id_1": {
                "path": "Sites.Site.Facilities.Facility.PremisesIdentifiers.PremisesIdentifier",
                "key_path_name": "IdentifierLabel",
                "key_path_value": "Custom ID",
                "value_path_name": "IdentifierValue",
                "required": True,
                "type": "string",
            },
            "gross_floor_area": {
                "path": "Sites.Site.Facilities.Facility.FloorAreas.FloorArea",
                "key_path_name": "FloorAreaType",
                "key_path_value": "Gross",
                "value_path_name": "FloorAreaValue",
                "required": True,
                "type": "double",
            },
            "net_floor_area": {
                "path": "Sites.Site.Facilities.Facility.FloorAreas.FloorArea",
                "key_path_name": "FloorAreaType",
                "key_path_value": "Net",
                "value_path_name": "FloorAreaValue",
                "required": False,
                "type": "double",
            },
            "footprint_floor_area": {
                "path": "Sites.Site.Facilities.Facility.FloorAreas.FloorArea",
                "key_path_name": "FloorAreaType",
                "key_path_value": "Footprint",
                "value_path_name": "FloorAreaValue",
                "required": False,
                "type": "double",
            },
        }
    }

    def __init__(self):
        self.filename = None
        self.data = None
        self.raw_data = None

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
                    namespaces={'http://nrel.gov/schemas/bedes-auc/2014': None}
                )
        else:
            raise Exception("File not found: {}".format(filename))

        return True

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
        messages = []
        errors = False
        for k, v in struct['return'].items():
            path = ".".join([struct['root'], v['path']])
            value = self._get_node(path, data, [])

            try:
                if v.get('key_path_name', None) and v.get('value_path_name', None) and v.get(
                    'key_path_value', None):
                    value = _lookup_sub(
                        value,
                        v.get('key_path_name'),
                        v.get('key_path_value'),
                        v.get('value_path_name'),
                    )

                    # check if the value is not defined and if it is required
                    if not value:
                        if v.get('required'):
                            messages.append(
                                "Could not find required value for sub-lookup of {}:{}".format(
                                    v.get('key_path_name'), v.get('key_path_value')))
                            errors = True
                            continue
                        else:
                            continue

                if value:
                    # catch some errors
                    if isinstance(value, list):
                        messages.append("Could not find single entry for '{}'".format(path))
                        errors = True
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
                        messages.append("Unknown cast type of {} for '{}'".format(v['type'], path))

                    res[k] = value
                else:
                    if v['required']:
                        messages.append("Could not find required value for '{}'".format(path))
                        errors = True
            except Exception as err:
                message = "Error processing {}:{} with error: {}".format(k, v, err)
                messages.append(message)
                errors = True

        # manually add in parsing of measures and reports because they are a bit different than
        # a straight mapping
        measures = self._get_node('Audits.Audit.Measures.Measure', data, [])
        for m in measures:
            category = m['TechnologyCategories']['TechnologyCategory'].keys()[0]
            new_data = {
                'property_measure_name': m.get('@ID'),  # This will be the IDref from the scenarios
                'category': _snake_case(category),
                'name': m['TechnologyCategories']['TechnologyCategory'][category]['MeasureName']
            }
            for k, v in m.items():
                if k in ['@ID', 'PremisesAffected', 'TechnologyCategories']:
                    continue
                new_data[_snake_case(k)] = v

            # fix the names of the measures for "easier" look up... doing in separate step to
            # fit in single line. Cleanup -- when?
            new_data['name'] = _snake_case(new_data['name'])
            res['measures'].append(new_data)

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
        scenarios = self._get_node('Audits.Audit.Report.Scenarios.Scenario', data, [])
        for s in scenarios:
            new_data = {
                'id': s.get('@ID'),
                'name': s.get('ScenarioName'),
            }

            if s.get('ScenarioType'):
                node = s['ScenarioType'].get('PackageOfMeasures')
                if node:
                    ref_case = self._get_node('ReferenceCase', node, [])
                    if ref_case and ref_case.get('@IDref'):
                        new_data['reference_case'] = ref_case.get('@IDref')
                    new_data['annual_savings_site_energy'] = node.get('AnnualSavingsSiteEnergy')

                    new_data['measures'] = []
                    measures = self._get_node('MeasureIDs.MeasureID', node, [])
                    if isinstance(measures, list):
                        for measure in measures:
                            if measure.get('@IDref', None):
                                new_data['measures'].append(measure.get('@IDref'))
                    else:
                        if isinstance(measures, (str, unicode)):
                            # the measure is there, but it does not have an idref
                            continue
                        else:
                            if measures.get('@IDref', None):
                                new_data['measures'].append(measures.get('@IDref'))

            res['scenarios'].append(new_data)

        return res, errors, messages

    def process(self, process_struct=ADDRESS_STRUCT):
        """Process the BuildingSync file based ont he process structure.

        :param process_struct: dict, structure on how to extract data from file and save into dict
        :return: list, [dict, list, list], [results, list of errors, list of messages]
        """
        # API call to BuildingSync Validator on other server for appropriate use case
        # usecase = new_use_case
        return self._process_struct(process_struct, self.raw_data)
