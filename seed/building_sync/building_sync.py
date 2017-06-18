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
    def __init__(self):
        self.filename = None
        self.data = None

    @property
    def pretty_print(self):
        """
        Print the JSON to the screen
        :return: None
        """
        print(json.dumps(self.data, indent=2))

    def import_file(self, filename):
        self.filename = filename
        self.address_line_1 = None
        self.city = None

        if os.path.isfile(filename):
            with open(filename, 'rU') as xmlfile:
                self.data = xmltodict.parse(
                    xmlfile.read(),
                    process_namespaces=True,
                    namespaces={'http://nrel.gov/schemas/bedes-auc/2014': None}
                )

                self.process()
        else:
            raise Exception("File not found: {}".format(filename))

        # self.pretty_print
        #
        return True

    def _get_node(self, path, node, results=[]):
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
                else:
                    self._get_node(new_path, new_node, results)
                    break

        if len(results) == 1:
            return results[0]
        else:
            return results

    def process(self):
        """Process a BuildingSync file

        This is just a stub, will be filled in over time to get the remainder of the objects
        """
        p = 'Audits.Audit.Sites.Site.Address.StreetAddressDetail.Simplified.StreetAddress'
        self.address_line_1 = self._get_node(p, self.data, [])
        p = 'Audits.Audit.Sites.Site.Address.City'
        self.city = self._get_node(p, self.data, [])
