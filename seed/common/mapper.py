# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author Dan Gunter <dkgunter@lbl.gov>
"""
from fnmatch import fnmatchcase
import json
import logging
import os
import re

from config.settings.dev import SEED_DATADIR

_log = logging.getLogger(__name__)

LINEAR_UNITS = set([u'ft', u'm', u'in'])  # ??more??


def get_pm_mapping(version, columns, include_none=False):
    """Create and return Portfolio Manager (PM) mapping for
    a given version of PM and the given list of column names.

    Args:
      version (str): Version in format 'x.y[.z]'
      columns (list): A list of [column_name, field, {metadata}]
      include_none (bool): If True, add {column:None} for unmatched columns.
    Return:
       (dict) of {column:MapItem}, where `column` is one of the values in
       the input list. If `include_none` was True, then all columns should
       be in the output.
    """
    conf = MappingConfiguration()
    version_parts = version.split('.')
    mp = conf.pm(version_parts)
    result = {}
    for col in columns:
        mapped = mp.get(col, None)
        if mapped:
            result[col] = mapped
        elif include_none:
            result[col] = None
        else:
            pass  # nothing added to result
    _log.debug("get_pm_mapping: result={}".format(
        '\n'.join(['{:40s} => {}'.format(k[:40], v) for k, v in result.iteritems()])))

    return result


class Programs(object):
    """Enumeration of program names.
    """
    PM = "PortfolioManager"


class MappingConfiguration(object):
    """Factory for creating Mapping objects
    from configurations.
    """

    def __init__(self):
        f = open(os.path.join(SEED_DATADIR, "mappings.conf"))
        self.conf = json.load(f)

    def pm(self, version):
        """Get Portfolio Manager mapping for given version.

        Args:
          version (tuple): A list of ints/strings (major, minor, ..)
        Raises:
          ValueError, if no mapping is found
        """
        files = self.conf[Programs.PM]
        filename = self._match_version(version, files)
        if filename is None:
            raise ValueError("No PortfolioManager mapping found "
                             "for version {}".format(version))
        path = os.path.join(SEED_DATADIR, filename)
        f = open(path, 'r')
        return Mapping(f)

    def _match_version(self, version, file_list):
        str_ver = '.'.join(map(str, version))
        for f in file_list:
            ver = f['version']
            if fnmatchcase(str_ver, ver):
                return f['file']
        return None


class Mapping(object):
    """Mapping from one set of fields to another.
    The mapping can be many:1.
    The lookup may be by static string or regular expression.
    """
    META_BEDES = 'bedes'  # BEDES-compliant flag
    META_TYPE = 'type'  # Type value
    META_NUMERIC = 'numeric'  # Is-numeric

    def __init__(self, fileobj, encoding=None, regex=False, spc_or_underscore=True,
                 ignore_case=True, normalize_units=True):
        """Initialize/create mapping from an input file-like object.
        Format of the file must be JSON, specifically:

        { 'source_field': ['target_field', {metadata}],  .. }

        :param fileobj: Object that can be wrapped with `json.load()`
        :param encoding str: Name of encoding of input keys. This
         function will re-encode the input as utf-8. A typical encoding
         for data from Windows or Excel is 'latin_1'.
        :param regex bool: If true, interpret lookup keys as regular expressions,
          otherwise do simple string key lookups.
          Note that spc_or_underscore and/or ignore_case flags force
          regular expressions to be used.
        :param spc_or_underscore bool: If true, allow spaces and underscores
            to be interchangeable
        :param ignore_case bool: If true, be case-insensitive in matches
        :param normalize_units bool: If true, allow superscripts etc. in units
        :raises: Exceptions from `json.load()` of invalid input file
        """
        self.data = json.load(fileobj)
        # figure out whether we will be using a regular expression
        self._regex = regex or ignore_case or spc_or_underscore
        # set up regex
        self._regex_flags = re.IGNORECASE if ignore_case else 0
        # set up transforms
        self._transforms = []
        if encoding is not None:
            self._encoding = encoding
            self._transforms.append(self._to_unicode)
            self._transforms.append(self._fix_superscripts)
        if normalize_units:
            self._transforms.append(self._normalize_units)
        if self._regex and not regex:  # input is literal
            self._transforms.append(self._re_escape)  # so escape it first
        if spc_or_underscore:
            self._transforms.append(self._space_or_underscore)

    def __str__(self):
        return "Length: {length}, Use-Regex={re}".format(length=len(self.data),
                                                         re=self._regex)

    def __getitem__(self, key):
        """Get value for corresponding key.

        :param key str: Key, which will be interpreted as a regular
         expression if `regex=True` was passed to constructor.
        :return: (MapItem) Item to which it is mapped
        """
        for t in self._transforms:
            key = t(key)
        if self._regex:
            re_key, val = re.compile(key, flags=self._regex_flags), None
            for k, value in self.data.items():
                if re_key.match(k):
                    val = value
                    break
            if val is None:
                raise KeyError(key)
        else:
            val = self.data[key]
        return MapItem(key, val)

    def get(self, key, default=None):
        """Wrapper around __getitem__ that will return the default instead
        of raising KeyError if the item is not found.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        """Get list of source keys.

        Return:
           (list) Source keys
        """
        tkeys = []
        for key in self.data.keys():
            for t in self._transforms:
                key = t(key)
            tkeys.append(key)
        return tkeys

    def apply(self, keys):
        """Get value for a list of keys.

        :param keys: List of keys (strings)
        :return: A pair of values. The first is a mapping {key: value} of
            the keys that matched. The second is a list [key, key, ..] of
            those that didn't.
        """
        matched, nomatch = {}, []
        for key in keys:
            r = self.get(key)
            if r is None:
                nomatch.append(key)
            else:
                matched[key] = r
        return matched, nomatch

    #
    # --- Transforms ----
    #

    def _to_unicode(self, key):
        if isinstance(key, unicode):
            return key
        return unicode(key, self._encoding)

    def _fix_superscripts(self, key):
        key = key.replace(u'\u00B2', u'2')
        key = key.replace(u'\u00B3', u'3')
        return key

    @staticmethod
    def _re_escape(key):
        for special in ('\\', '(', ')', '?', '*', '+', '.', '{', '}', '^', '$'):
            key = key.replace(special, '\\' + special)
        return key

    def _normalize_units(self, key):
        """Allow for variations on unit dimensions

            ft_ => ft2   - superscript 2 mangled to '_'
            ft^2 => ft2
            ft^2 => ft3

        Replace 'ft' by other linear measures in LINEAR_UNITS
        """
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
        return key

    @staticmethod
    def _space_or_underscore(key):
        """Replace spaces with spaces OR underscores, as a regular expr.
        Also compresses multiple spaces to a single one, and allows multiple
        spaces or underscores in the resulting expression.

        For example:
           "foo  bar__baz" -> "foo( |_)+bar( |_)+baz"
        """
        key = key.replace('_', ' ').replace('  ', ' ')
        return key.replace(' ', '( |_)+')


class MapItem(object):
    """Wrapper around a mapped item.

    An object will be created with the following attributes:

    - source => The source field from which we mapped
    - field => The field to which we mapped
    - is_bedes => flag, whether this field is BEDES-compliant
    - is_numeric => whether the data is numeric (or string)
    """
    def __init__(self, key, item):
        """Construct from key and item.
        :param key: The source field for the mapping
        :param item: The target field and metadata for the mapping.
          This may also be None, to indicate a failed mapping
        """
        self.source = key
        if item is None:
            self.field, self.is_bedes, self.is_numeric = None, False, False
        else:
            self.field = item[0]
            self.is_bedes = item[1][Mapping.META_BEDES]
            self.is_numeric = item[1][Mapping.META_TYPE] == 'float'

    def as_json(self):
        return [self.field, {Mapping.META_BEDES: self.is_bedes,
                             Mapping.META_NUMERIC: self.is_numeric}]

    def __str__(self):
        return json.dumps(self.as_json())
