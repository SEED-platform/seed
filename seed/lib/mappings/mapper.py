# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md

:author Dan Gunter <dkgunter@lbl.gov>
"""
import json
import logging
import os
import re
from collections import OrderedDict
from os.path import dirname, join, realpath

from past.builtins import basestring
from unidecode import unidecode

LINEAR_UNITS = set(['ft', 'm', 'in'])
MAPPING_DATA_DIR = join(dirname(realpath(__file__)), 'data')

_log = logging.getLogger(__name__)


def _sanitize_and_convert_keys_to_regex(key):
    """Replace spaces with spaces OR underscores, as a regular expr.
    Also compresses multiple spaces to a single one, and allows multiple
    spaces or underscores in the resulting expression.

    For example:
       "foo  bar__baz" -> "foo( |_)+bar( |_)+baz"
    """

    # force unicode
    # TODO: python3 check if this to run in python3
    if isinstance(key, basestring):
        key = unidecode(key)

    # fix superscripts - copied from old code
    found = False
    for pfx in LINEAR_UNITS:
        if pfx not in key:
            continue
        for (sfx, repl) in ('_', '2'), ('^2', '2'), ('^3', '3'):
            s = pfx + sfx
            p = key.find(s)
            if p >= 0:  # yes, the unit has a dimension
                key = key[:p + len(pfx)] + repl + key[p + len(s):]
                found = True
                break
        if found:
            break

    # escape special characters before regexing.
    for special in ('\\', '(', ')', '?', '*', '+', '.', '{', '}', '^', '$'):
        key = key.replace(special, '\\' + special)

    # convert underscores to white space
    key = key.replace('_', ' ').replace('  ', ' ')
    # collapse whitespace
    key = re.sub(r'\s+', ' ', key).strip()

    # convert white space to regex for space or underscore (repeated)
    key = key.replace(' ', '( |_)+')

    return re.compile(key, re.IGNORECASE)


def create_column_regexes(raw_columns):
    """
    Take the columns in the format below and sanitize the keys and add
    in the regex.

    :param raw_data: list of strings (columns names from imported file)

    :return: list of dict

    .. code:

        Result shall look like:

        [
            {'regex': <_sre.SRE_Pattern object at 0x10f151a50>, 'raw': 'has_underscores'},
            {'regex': <_sre.SRE_Pattern object at 0x10f10e870>, 'raw': 'has  multi spaces'}
        ]
    """
    if not raw_columns:
        _log.debug("No raw_columns provided!")
        return []

    # clean up the comparing columns
    new_list = []
    for c in raw_columns:
        new_data = {}
        new_data['raw'] = c
        new_data['regex'] = _sanitize_and_convert_keys_to_regex(c)
        new_list.append(new_data)

    return new_list


def get_pm_mapping(raw_columns, mapping_data=None, resolve_duplicates=True):
    """
    Create and return Portfolio Manager (PM) mapping for a given version of PM and the given
    list of column names.

    The method will take the raw_columns (from the CSV/XLSX file) and attempt to normalize the
    column names so that they can be mapped to the data in the pm-mapping.json['from_field'].

    .. code:
        [
            {
                "display_name": "Address Line 1",
                "to_field": "address_line_1",
                "to_table_name": "PropertyState",
                "from_field": "Address 1",
                "units": "",
                "type": "string",
                "schema": ""
            }
        ]

    .. code:

        # Without duplicates

        {
            'Address 1': ('PropertyState', 'address_line_1', 100),
            'Property ID': ('PropertyState', 'pm_property_id', 100),
            'Portfolio Manager Property ID': ('PropertyState', 'Portfolio Manager Property ID', 100),
            'Address_1': ('PropertyState', 'Address_1', 100)
        }

        # With duplicates

        {
            'Address 1': ('PropertyState', 'address_line_1', 100),
            'Property ID': ('PropertyState', 'pm_property_id', 100),
            'Portfolio Manager Property ID': ('PropertyState', 'pm_property_id', 100),
            'Address_1': ('PropertyState', 'address_line_1', 100)
        }



    """
    from_columns = create_column_regexes(raw_columns)

    if not mapping_data:
        f = open(os.path.join(MAPPING_DATA_DIR, "pm-mapping.json"))
        mapping_data = json.load(f)

    # transform the data into the format expected by the mapper. (see mapping_columns.final_mappings)
    final_mappings = OrderedDict()
    for c in from_columns:
        column_found = False
        for d in mapping_data:
            if c['regex'].match(d['from_field']):
                # Assume that the mappings are 100% accurate for now.
                final_mappings[c['raw']] = (d['to_table_name'], d['to_field'], 100)
                column_found = True
                continue

        if not column_found:
            # if we get here then the columns was never found
            _log.debug("Could not find applicable mappings, resorting to raw field ({}) in PropertyState".format(c['raw']))
            final_mappings[c['raw']] = ('PropertyState', c['raw'], 100)

    # verify that there are no duplicate matchings
    if resolve_duplicates:

        # get the set of mappings
        mappings = []
        for v in final_mappings.values():
            mappings.append(v)

        unique_mappings = set()
        for k, v in final_mappings.items():
            if v not in unique_mappings:
                unique_mappings.add(v)
            else:
                i = 1
                base = v[1]
                while v in unique_mappings:
                    new_v = base + "_duplicate_{}".format(i)
                    v = (v[0], new_v, v[2])
                    i += 1

                unique_mappings.add(v)
                final_mappings[k] = v

    return final_mappings
