# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""
import json
import logging
import os
import re
from os.path import realpath, join, dirname

LINEAR_UNITS = set([u'ft', u'm', u'in'])
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
    if not isinstance(key, unicode):
        key = unicode(key)

    # fix superscripts
    key = key.replace(u'\u00B2', u'2')
    key = key.replace(u'\u00B3', u'3')

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
    key = re.sub('\s+', ' ', key).strip()

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

    # clean up the comparing columns
    new_list = []
    for c in raw_columns:
        new_data = {}
        new_data['raw'] = c
        new_data['regex'] = _sanitize_and_convert_keys_to_regex(c)
        new_list.append(new_data)

    return new_list


def get_pm_mapping(raw_columns, mapping_data=None):
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

    """

    from_columns = create_column_regexes(raw_columns)

    if not mapping_data:
        f = open(os.path.join(MAPPING_DATA_DIR, "pm-mapping.json"))
        mapping_data = json.load(f)

    # transform the data into the format expected by the mapper. (see mapping_columns.final_mappings)
    final_mappings = {}
    for d in mapping_data:
        for c in from_columns:
            if c['regex'].match(d['from_field']):
                # Assume that the mappings are 100% accurate for now.
                final_mappings[c['raw']] = (d['to_table_name'], d['to_field'], 100)

    # TODO: resolve any duplicates here
    # verify that there are no duplicate matchings

    return final_mappings
