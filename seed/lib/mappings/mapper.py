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
from fnmatch import fnmatchcase
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

    # remove underscores and convert white space
    key = key.replace('_', ' ').replace('  ', ' ')

    # convert white space to regex for space or underscore (repeated)
    key = key.replace(' ', '( |_)+')

    return re.compile(key, re.IGNORECASE)


def get_pm_mapping(raw_columns, include_nones):
    """Create and return Portfolio Manager (PM) mapping for
    a given version of PM and the given list of column names.

    Args:
      from_columns (list): A list of [column_name, field, {metadata}]
    Return:
    """

    f = open(os.path.join(MAPPING_DATA_DIR, "pm-mapping.json"))
    data = json.load(f)

    # clean up the comparing columns
    from_columns = []
    for c in raw_columns:
        new_data = {}
        new_data['raw'] = c
        new_data['regex'] = _sanitize_and_convert_keys_to_regex(c)
        from_columns.append(new_data)

    # transform the data into the format expected by the mapper. (see mapping_columns.final_mappings)
    final_mappings = {}
    for d in data:
        for c in from_columns:
            if c['regex'].match(d['from_field']):
                # Assume that the mappings are 100% accurate for now.
                final_mappings[c['raw']] = (d['to_table_name'], d['to_field'], 100)

    # TODO: resolve any duplicates here
    # verify that there are no duplicate matchings

    return final_mappings


class Programs(object):
    PM = "PortfolioManager"


class MappingConfiguration(object):

    def __init__(self):
        print "DEPRECATED"


class Mapping(object):

    def __init__(self, fileobj, encoding=None, regex=False,
                 spc_or_underscore=True,
                 ignore_case=True, normalize_units=True):
        print "DEPRECATED"


class MapItem(object):
    """Wrapper around a mapped item.

    An object will be created with the following attributes:

    - source => The source field from which we mapped
    - table => The seed table to which we mapped
    - field => The seed field to which we mapped
    """

    def __init__(self, key, item):
        print "DEPRECATED!"
