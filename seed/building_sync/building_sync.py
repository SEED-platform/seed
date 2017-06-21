# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author nicholas.long@nrel.gov
"""

import json
import os

import xmltodict


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
        "root": "Audits.Audit.Sites.Site",
        "return": {
            "address_line_1": {
                "path": "Address.StreetAddressDetail.Simplified.StreetAddress",
                "required": True,
                "type": "string",
            },
            "city": {
                "path": "Address.City",
                "required": True,
                "type": "string",
            },
            "state": {
                "path": "Address.State",
                "required": True,
                "type": "string",
            },
            "longitude": {
                "path": "Longitude",
                "required": True,
                "type": "double"
            },
            "latitude": {
                "path": "Latitude",
                "required": True,
                "type": "double",
            },
            "custom_id_1": {
                "path": "Facilities.Facility.@ID",
                "required": True,
                "type": "string",
            },
            "year_built": {
                "path": "Facilities.Facility.YearOfConstruction",
                "required": True,
                "type": "integer",
            },
            "property_type": {
                "path": "Facilities.Facility.FacilityClassification",
                "required": True,
                "type": "string",
            },
            "occupancy_type": {
                "path": "Facilities.Facility.OccupancyClassification",
                "required": True,
                "type": "string",
            },
            "floors_above_grade": {
                "path": "Facilities.Facility.FloorsAboveGrade",
                "required": True,
                "type": "integer",
            },
            "floors_below_grade": {
                "path": "Facilities.Facility.FloorsBelowGrade",
                "required": True,
                "type": "integer",
            },
            "premise_identifier": {
                "path": "Facilities.Facility.PremisesIdentifiers.PremisesIdentifier",
                "key_path_name": "IdentifierLabel",
                "key_path_value": "Assessor parcel number",
                "value_path_name": "IdentifierValue",
                "required": True,
                "type": "string",
            },
            "gross_floor_area": {
                "path": "Facilities.Facility.FloorAreas.FloorArea",
                "key_path_name": "FloorAreaType",
                "key_path_value": "Gross",
                "value_path_name": "FloorAreaValue",
                "required": True,
                "type": "double",
            },
            "net_floor_area": {
                "path": "Facilities.Facility.FloorAreas.FloorArea",
                "key_path_name": "FloorAreaType",
                "key_path_value": "Net",
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
            return None
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
                for k, v in item.iteritems():
                    if k == key_path_name and v == key_path_value:
                        found = True

                    if found and k == value_path_name:
                        return v

        res = {}
        messages = []
        errors = False
        for k, v in struct['return'].items():
            path = ".".join([struct['root'], v['path']])
            value = self._get_node(path, data, [])

            if value is not None:
                if v.get('key_path_name', None) and \
                    v.get('value_path_name', None) and \
                        v.get('key_path_value', None):
                    value = _lookup_sub(
                        value,
                        v.get('key_path_name'),
                        v.get('key_path_value'),
                        v.get('value_path_name'),
                    )

                # catch some errors
                if isinstance(value, list):
                    messages.append("Could not find single entry for '{}'".format(path))
                    errors = True
                    break

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
                    messages.append("Could not find '{}'".format(path))
                    errors = True

        return res, errors, messages

    def process(self, process_struct=ADDRESS_STRUCT):
        """Process the BuildingSync file based ont he process structure.

        :param process_struct: dict, structure on how to extract data from file and save into dict
        :return: list, [dict, list, list], [results, list of errors, list of messages]
        """
        # API call to BuildingSync Validator on other server for appropriate use case
        # usecase = new_use_case
        return self._process_struct(process_struct, self.raw_data)
